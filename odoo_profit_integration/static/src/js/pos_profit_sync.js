odoo.define('odoo_profit_integration.pos_profit_sync', function (require) {
    "use strict";

    const models = require('point_of_sale.models');
    const PaymentScreen = require('point_of_sale.PaymentScreen');
    const Registries = require('point_of_sale.Registries');
    const { Gui } = require('point_of_sale.Gui');

    // 1. Sobrescribir el Modelo de Orden para estampar Tasa de Cambio Dinámica
    const PosModelSuper = models.Order.prototype;
    models.Order = models.Order.extend({
        initialize: function (attributes, options) {
            PosModelSuper.initialize.apply(this, arguments);
            // Capturamos la tasa de cambio vigente al crear la orden
            this.exchange_rate_applied = this.pos.currency.rate || 1.0;
        },
        export_as_JSON: function () {
            const json = PosModelSuper.export_as_JSON.apply(this, arguments);
            json.exchange_rate_applied = this.exchange_rate_applied;
            return json;
        }
    });

    // 2. Control Estricto en la Pantalla de Pago (PaymentScreen)
    const ProfitPaymentScreen = (PaymentScreen) =>
        class extends PaymentScreen {
            async validateOrder(isForceValidate) {
                const order = this.env.pos.get_order();

                // Regla 1: Validar Modo Offline (Farmacias no pueden vender offline, Restaurantes sí pero sin pasarelas)
                if (this.env.pos.config.profit_business_model === 'pharmacy' && !this.env.pos.synch.status === 'connected') {
                    Gui.showPopup('ErrorPopup', {
                        title: 'Modo Offline Bloqueado',
                        body: 'Las farmacias requieren conexión síncrona para validar lotes y vencimientos en Profit Plus.',
                    });
                    return;
                }

                // Regla 2: Prohibir texto libre en justificaciones de devoluciones
                if (order.get_total_with_tax() < 0) {
                    if (!order.get_refunded_order_id()) {
                        Gui.showPopup('ErrorPopup', {
                            title: 'Devolución Invalida',
                            body: 'Toda devolución debe estar referenciada a una factura original de Profit.',
                        });
                        return;
                    }
                }

                // Si pasa las validaciones, procede con el flujo normal
                await super.validateOrder(isForceValidate);
            }
        };

    Registries.Component.extend(PaymentScreen, ProfitPaymentScreen);

    return ProfitPaymentScreen;
});
