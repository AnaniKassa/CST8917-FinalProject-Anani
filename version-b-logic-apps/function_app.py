import azure.functions as func
import logging
import json
import os
from azure.servicebus import ServiceBusClient, ServiceBusMessage
from azure.data.tables import TableServiceClient
from datetime import datetime

app = func.FunctionApp()

# =========================
# SUBMIT EXPENSE (HTTP → SERVICE BUS QUEUE)
# =========================
@app.route(route="submit_expense", methods=["POST"], auth_level=func.AuthLevel.ANONYMOUS)
def submit_expense(req: func.HttpRequest) -> func.HttpResponse:
    try:
        data = req.get_json()
    except:
        return func.HttpResponse("Invalid JSON", status_code=400)

    conn_str = os.environ["SERVICEBUS_CONNECTION_STRING"]
    queue_name = os.environ["SERVICEBUS_QUEUE_NAME"]

    with ServiceBusClient.from_connection_string(conn_str) as client:
        sender = client.get_queue_sender(queue_name)
        with sender:
            sender.send_messages(ServiceBusMessage(json.dumps(data)))

    return func.HttpResponse("Expense submitted to queue", status_code=200)


# =========================
# VALIDATE EXPENSE (LOGIC APP CALLS THIS)
# =========================
@app.route(route="validate_expense", methods=["POST"], auth_level=func.AuthLevel.ANONYMOUS)
def validate_expense(req: func.HttpRequest) -> func.HttpResponse:
    try:
        data = req.get_json()
    except:
        return func.HttpResponse(json.dumps({"isValid": False, "error": "Invalid JSON"}), status_code=400)

    required = ["employeeName", "employeeEmail", "amount", "category", "description", "managerEmail"]
    valid_categories = ["travel", "meals", "supplies", "equipment", "software", "other"]

    for field in required:
        if field not in data:
            return func.HttpResponse(
                json.dumps({"isValid": False, "error": f"Missing {field}"}),
                mimetype="application/json",
                status_code=400
            )

    if data["category"] not in valid_categories:
        return func.HttpResponse(
            json.dumps({"isValid": False, "error": "Invalid category"}),
            mimetype="application/json",
            status_code=400
        )

    return func.HttpResponse(
        json.dumps({"isValid": True}),
        mimetype="application/json",
        status_code=200
    )


# =========================
# MANAGER DECISION (STORE IN TABLE STORAGE)
# =========================
@app.route(route="manager_decision", methods=["POST"], auth_level=func.AuthLevel.ANONYMOUS)
def manager_decision(req: func.HttpRequest) -> func.HttpResponse:
    try:
        data = req.get_json()
    except:
        return func.HttpResponse("Invalid JSON", status_code=400)

    table_name = os.environ["APPROVAL_TABLE_NAME"]
    conn_str = os.environ["AzureWebJobsStorage"]

    table_service = TableServiceClient.from_connection_string(conn_str)
    table_client = table_service.get_table_client(table_name)

    entity = {
        "PartitionKey": "approval",
        "RowKey": data["requestId"],
        "decision": data["decision"],
        "timestamp": str(datetime.utcnow())
    }

    table_client.upsert_entity(entity)

    return func.HttpResponse("Decision stored", status_code=200)
