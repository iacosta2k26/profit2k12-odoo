{
    'name': 'Odoo POS to Profit Plus 2k12 Integration',
    'version': '16.0.1.0.0',
    'category': 'Sales/Point of Sale',
    'summary': 'Integración estricta con ERP Profit Plus 2k12',
    'depends': ['point_of_sale'],
    'data': [
        'security/ir.model.access.csv',
    ],
    'assets': {
        'point_of_sale.assets': [
            'odoo_profit_integration/static/src/js/pos_profit_sync.js',
        ],
    },
    'installable': True,
    'application': False,
}
