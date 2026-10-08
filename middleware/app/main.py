from fastapi import FastAPI, HTTPException, Request
from app.models.schemas import PosOrderPayload
import pika
import json

app = FastAPI(title="Middleware Odoo -> Profit 2k12")

def get_rabbitmq_channel():
    # Placeholder para conexión robusta RabbitMQ
    connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
    return connection.channel()

@app.post("/api/v1/pos/orders", status_code=202)
async def ingest_pos_order(payload: PosOrderPayload):
    """
    Recibe la transacción de Odoo y la encola inmediatamente en RabbitMQ (Buffer / Modo Offline).
    """
    try:
        channel = get_rabbitmq_channel()
        channel.exchange_declare(exchange='pos_events', exchange_type='topic')
        
        routing_key = f"{payload.metadata.tenant_id}.pos.order.{payload.transaction.type}"
        
        channel.basic_publish(
            exchange='pos_events',
            routing_key=routing_key,
            body=payload.model_dump_json()
        )
        return {"status": "Accepted", "correlation_id": payload.metadata.correlation_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
