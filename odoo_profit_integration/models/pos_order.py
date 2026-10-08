from odoo import models, fields, api
import requests
import json
import uuid

class PosOrder(models.Model):
    _inherit = 'pos.order'

    profit_sync_status = fields.Selection([
        ('pending', 'Pendiente'),
        ('synced', 'Sincronizado'),
        ('failed', 'Fallido')
    ], string='Status Profit 2k12', default='pending')
    
    correlation_id = fields.Char(string="Correlation ID", copy=False)

    @api.model
    def _process_order(self, order, draft, existing_order):
        # Override nativo: Generar UUID y preparar payload
        res = super(PosOrder, self)._process_order(order, draft, existing_order)
        order_record = self.browse(res)
        
        if not order_record.correlation_id:
            order_record.correlation_id = str(uuid.uuid4())
            
        # El envío real se hará mediante un cron/worker o en tiempo real
        # Aquí iría el trigger hacia el Middleware Python
        
        return res
