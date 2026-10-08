import pika
import json
import logging
import requests
from pydantic import ValidationError
import sys
import os

# Ajustar path para importar schemas
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models.schemas import PosOrderPayload

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# URL del servicio WCF de Profit Plus (Ejemplo)
WCF_SERVICE_URL = "http://localhost:8080/ProfitIntegrationService.svc/ProcesarFactura"

def process_order(ch, method, properties, body):
    try:
        # 1. Decodificar y Validar con Pydantic
        payload_dict = json.loads(body)
        order_payload = PosOrderPayload(**payload_dict)
        logger.info(f"[x] Procesando orden {order_payload.transaction.order_id} - Tenant: {order_payload.metadata.tenant_id}")

        # 2. Transformar / Mapear IDs si es necesario consultando Redis (Simulado aquí)
        # 3. Enviar al WCF Service
        
        headers = {'Content-Type': 'application/json'}
        response = requests.post(
            WCF_SERVICE_URL, 
            json=payload_dict, 
            timeout=10 # Circuit breaker/Timeout
        )
        
        if response.status_code == 200:
            logger.info(f"[v] Factura {order_payload.transaction.order_id} integrada en Profit.")
            ch.basic_ack(delivery_tag=method.delivery_tag)
        else:
            logger.error(f"[!] Error WCF: {response.text}")
            # Enviar a Dead Letter Queue (DLQ) o reencolar según política
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

    except ValidationError as ve:
        logger.error(f"Error de validación JSON Contract: {ve}")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False) # DLQ
    except Exception as e:
        logger.error(f"Error interno del worker: {e}")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True) # Retry

def start_consuming():
    connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
    channel = connection.channel()
    
    channel.exchange_declare(exchange='pos_events', exchange_type='topic')
    result = channel.queue_declare(queue='profit_orders_queue', durable=True)
    queue_name = result.method.queue
    
    channel.queue_bind(exchange='pos_events', queue=queue_name, routing_key='*.pos.order.invoice')
    
    # QoS (Rate limiting: 5 mensajes a la vez para no saturar SQL Server)
    channel.basic_qos(prefetch_count=5)
    channel.basic_consume(queue=queue_name, on_message_callback=process_order)
    
    logger.info(' [*] Esperando mensajes de Odoo POS. Para salir presione CTRL+C')
    channel.start_consuming()

if __name__ == '__main__':
    # En producción esto correría como un daemon/servicio
    pass
