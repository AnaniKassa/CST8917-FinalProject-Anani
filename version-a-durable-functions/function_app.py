import azure.functions as func
import azure.durable_functions as df
import logging
import json
from datetime import timedelta
from typing import Any


app = df.DFApp(http_auth_level=func.AuthLevel.ANONYMOUS)

VALID_CATEGORIES = ["travel", "meals", "supplies", "equipment", "software", "other"]

# =========================
# START ORCHESTRATION
# =========================
@app.route(route="start")
@app.durable_client_input(client_name="client")
async def start(req: func.HttpRequest, client):
    data = req.get_json()
    instance_id = await client.start_new("orchestrator", None, data)

    return func.HttpResponse(f"Started: {instance_id}")


# =========================
# ORCHESTRATOR
# =========================
@app.orchestration_trigger(context_name="context")
def orchestrator(context: df.DurableOrchestrationContext):
    data = context.get_input()

    # Step 1: Validate
    valid = yield context.call_activity("validate", data)
    if not valid["isValid"]:
        return valid

    # Step 2: Auto approvey
    if data["amount"] < 100:
        result = {
            "status": "approved",
            "reason": "Auto-approved under $100"
        }
    else:
        # Step 3: Wait for manager OR timeout
        approval_event = context.wait_for_external_event("ManagerApproval")
        timeout = context.create_timer(context.current_utc_datetime + timedelta(seconds=30))

        winner = yield context.task_any([approval_event, timeout])

        if winner == approval_event:
            decision = approval_event.result
            result = {
                "status": decision,
                "reason": "Manager decision"
            }
        else:
            result = {
                "status": "escalated",
                "reason": "Timeout"
            }

    # Step 4: Notify
    yield context.call_activity("notify", {
        "email": data["employeeEmail"],
        "result": result
    })

    return result


# =========================
# VALIDATION
# =========================
@app.activity_trigger(input_name="input")
def validate(input: dict):
    data = input

    required = ["employeeName", "employeeEmail", "amount", "category", "description", "managerEmail"]

    for field in required:
        if field not in data:
            return {"isValid": False, "error": f"Missing {field}"}

    return {"isValid": True}

# =========================
# NOTIFICATION
# =========================
@app.activity_trigger(input_name="input")
def notify(input: dict):
    data = input

    logging.info(f"""
    --- EMAIL SIMULATION ---
    To: {data['email']}
    Status: {data['result']['status']}
    Reason: {data['result']['reason']}
    ------------------------
    """)
    return True

# =========================
# MANAGER RESPONSE
# =========================
@app.route(route="approve/{id}")
@app.durable_client_input(client_name="client")
async def approve(req: func.HttpRequest, client):
    instance_id = req.route_params.get("id")
    body = req.get_json()

    await client.raise_event(instance_id, "ManagerApproval", body["decision"])

    return func.HttpResponse("Manager decision sent")
