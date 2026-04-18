# CST8917 Final Project — Compare & Contrast: Expense Approval Workflow

**Course:** CST8917 — Serverless Applications  
**Project:** Dual implementation of an Expense Approval Workflow  
**Student:** [Your Name]  
**Student Number:** [Your Student Number]  
**Date:** [YYYY-MM-DD]

---

## 1. Project Overview

This project implements the **same expense approval workflow twice** using two Azure serverless approaches:

- **Version A:** Azure Durable Functions (code-first orchestration)
- **Version B:** Azure Logic Apps + Service Bus (visual/declarative orchestration)

The workflow is the same in both versions:

1. Receive an expense request.
2. Validate required fields and category.
3. Auto-approve if the amount is below $100.
4. For $100 or more, wait for manager approval.
5. If no decision arrives before timeout, escalate and auto-approve.
6. Send the employee an email with the final outcome.

The assignment is intentionally designed to compare **Durable Functions vs. Logic Apps** from real hands-on experience, including development speed, testability, error handling, human interaction, observability, and cost.

---

## 2. Repository Structure

```text
CST8917-FinalProject-YourName/
├── README.md
├── version-a-durable-functions/
│   ├── function_app.py
│   ├── requirements.txt
│   ├── host.json
│   ├── local.settings.example.json
│   └── test-durable.http
├── version-b-logic-apps/
│   ├── function_app.py
│   ├── requirements.txt
│   ├── local.settings.example.json
│   ├── test-expense.http
│   └── screenshots/
└── presentation/
    ├── slides.pptx
    └── video-link.md
```

---

## 3. Prerequisites

Before starting, install and set up:

- **VS Code**
- **Azure Functions extension** in VS Code
- **Azure CLI** (recommended)
- **Python 3.11 or 3.12**
- **Azure Functions Core Tools**
- **Azurite** for local storage emulation
- An **Azure subscription**
- Access to **Azure Portal**

---

## 4. Version A — Azure Durable Functions

### 4.1 What this version should do

Version A should use:

- an **HTTP trigger** to start the workflow
- a **Durable Orchestrator**
- **Activity functions** for validation, processing, and notification
- a **Human Interaction pattern** using:
  - `wait_for_external_event`
  - `create_timer`
- an **HTTP endpoint** for manager approval or rejection

This version should prove you can handle the workflow in code and wait for a human decision without blocking the function.

### 4.2 Recommended Azure resources

Create these resources for Version A:

- **Function App** (Python, Linux, Consumption)
- **Storage Account** (required by Durable Functions)
- **Application Insights** (optional but useful for debugging)
- **Email sending service** for notifications  
  Recommended: SendGrid or another email API you can call from Python

### 4.3 Step-by-step build plan

#### Step 1 — Create the project in VS Code

1. Open VS Code.
2. Create a new folder for the project.
3. Open that folder in VS Code.
4. Open the Command Palette with `F1`.
5. Run **Azure Functions: Create New Project...**
6. Choose:
   - **Language:** Python
   - **Python interpreter:** your Python 3.11 or 3.12 environment
   - **Template:** Skip for now
   - **Open project:** Open in current window

This gives you a clean Azure Functions project to build on.

#### Step 2 — Install dependencies

In `version-a-durable-functions/requirements.txt`, include at least:

```txt
azure-functions
azure-functions-durable
sendgrid
```

If you use another email provider, add the package needed for that service.

Then install packages in your virtual environment:

```bash
python -m pip install -r requirements.txt
```

#### Step 3 — Configure local settings

Create `local.settings.example.json` with placeholder values only.

Example:

```json
{
  "IsEncrypted": false,
  "Values": {
    "AzureWebJobsStorage": "UseDevelopmentStorage=true",
    "FUNCTIONS_WORKER_RUNTIME": "python",
    "SENDGRID_API_KEY": "your-sendgrid-api-key",
    "EMAIL_FROM": "your-verified-sender@example.com",
    "EMAIL_TO_DEFAULT": "employee@example.com",
    "APPROVAL_TIMEOUT_MINUTES": "30"
  }
}
```

Keep real secrets out of GitHub.

#### Step 4 — Define the expense payload

Your request body should contain at least:

- `employeeName`
- `employeeEmail`
- `amount`
- `category`
- `description`
- `managerEmail`

Use one JSON shape for both versions so the comparison is fair.

Example:

```json
{
  "employeeName": "Jane Doe",
  "employeeEmail": "jane.doe@example.com",
  "amount": 175,
  "category": "travel",
  "description": "Taxi and hotel for client visit",
  "managerEmail": "manager@example.com"
}
```

#### Step 5 — Implement the function roles

In `function_app.py`, create these functions:

1. **Start function**  
   HTTP-triggered function that starts the orchestration.

2. **Orchestrator function**  
   Handles the full workflow:
   - validate input
   - branch on amount
   - wait for manager approval when needed
   - handle timeout
   - call notification activity

3. **Activity function: validate_expense**  
   Validates required fields and category.

4. **Activity function: prepare_decision**  
   Builds the final status object (`approved`, `rejected`, or `escalated`).

5. **Activity function: send_notification**  
   Sends an email to the employee.

6. **Manager response HTTP function**  
   Accepts manager approval/rejection and raises a durable event to the waiting orchestration.

#### Step 6 — Build the orchestrator logic

Use this sequence in the orchestrator:

1. Call `validate_expense`.
2. If validation fails, stop and return a validation error result.
3. If `amount < 100`:
   - mark as `approved`
   - call `send_notification`
   - return
4. If `amount >= 100`:
   - create a durable timer for the timeout window
   - wait for an external event such as `"ManagerDecision"`
   - cancel the timer if a decision arrives
   - if the decision is `"approved"` or `"rejected"`, use that outcome
   - if the timer wins, mark as `escalated` and auto-approve
   - call `send_notification`

This is the part that demonstrates the Durable Functions **Human Interaction pattern**.

#### Step 7 — Add the manager response endpoint

Add a route such as:

```text
POST /api/manager-response/{instanceId}
```

That endpoint should:

1. Read the approval decision from the request body.
2. Find the correct orchestration instance.
3. Raise the durable event named `ManagerDecision`.
4. Return a success response.

Use it to simulate the manager approving or rejecting requests during testing.

#### Step 8 — Test locally with `test-durable.http`

Create `version-a-durable-functions/test-durable.http` with test cases for:

1. Expense under $100 → auto-approved
2. Expense >= $100 with manager approval
3. Expense >= $100 with manager rejection
4. Expense >= $100 with no response before timeout
5. Missing required fields
6. Invalid category

For the approval/rejection cases, first start the orchestration, then call the manager response endpoint with the returned instance ID.

#### Step 9 — Run Azurite and start the app

1. Start **Azurite**.
2. Run the function app locally in VS Code.
3. Confirm the endpoints appear in the terminal.
4. Run your HTTP tests.

#### Step 10 — Deploy to Azure

1. Create a **Function App** in Azure.
2. Use the same runtime and region as your storage account.
3. Add the production app settings.
4. Deploy from VS Code.
5. Retest all scenarios in Azure.

### 4.4 What to capture for evidence

Save screenshots of:

- the orchestration runs
- validation failures
- approved and rejected outcomes
- timeout/escalation outcome
- email notification evidence

---

## 5. Version B — Azure Logic Apps + Service Bus

### 5.1 What this version should do

Version B should use:

- a **Service Bus queue** for incoming expense requests
- a **Logic App** to orchestrate the workflow
- an **Azure Function** for validation
- a **Service Bus topic** with filtered subscriptions for outcomes
- an email notification step for the employee

The assignment leaves the manager approval step open, so this version should use a reasonable workaround and document it clearly.

### 5.2 Recommended design choice for manager approval

A practical choice is:

- send the manager an approval request
- store the current approval state in a small table or similar storage
- let the Logic App poll for a decision using a **Do Until** loop with a delay
- stop when a decision arrives or when the timeout expires

This gives you a clear way to simulate waiting without Durable Functions.

### 5.3 Recommended Azure resources

Create these resources for Version B:

- **Service Bus namespace** in **Standard** tier
- **Service Bus queue** for incoming expenses
- **Service Bus topic** for outcomes
- **Topic subscriptions** for approved, rejected, and escalated
- **Logic App**
- **Function App** for validation
- **Storage Account** if you use table storage for approval status
- **Email connector** in Logic Apps, such as Outlook.com or Office 365 Outlook

### 5.4 Step-by-step build plan

#### Step 1 — Create the Service Bus namespace

1. Open Azure Portal.
2. Create a resource group if needed.
3. Create a Service Bus namespace.
4. Choose **Standard** pricing tier.

Standard is required because topics and subscriptions are needed for the outcome routing.

#### Step 2 — Create the queue and topic

Create:

- Queue: `expense-requests`
- Topic: `expense-outcomes`

Then create subscriptions under the topic:

- `approved-sub`
- `rejected-sub`
- `escalated-sub`

Add SQL filters on the subscriptions so each one only receives the matching label.

Example filters:

- `sys.label = 'approved'`
- `sys.label = 'rejected'`
- `sys.label = 'escalated'`

#### Step 3 — Create the Azure Function project for Version B

In VS Code:

1. Create a new Azure Functions project in the `version-b-logic-apps` folder.
2. Use Python.
3. Skip the template for now.

Add dependencies such as:

```txt
azure-functions
azure-servicebus
azure-data-tables
```

If you create a helper function to submit test requests, the Service Bus SDK will let you push messages into the queue from your local HTTP test file.

#### Step 4 — Configure local settings

Create `local.settings.example.json` with placeholders:

```json
{
  "IsEncrypted": false,
  "Values": {
    "AzureWebJobsStorage": "UseDevelopmentStorage=true",
    "FUNCTIONS_WORKER_RUNTIME": "python",
    "SERVICEBUS_CONNECTION_STRING": "your-service-bus-connection-string",
    "SERVICEBUS_QUEUE_NAME": "expense-requests",
    "SERVICEBUS_TOPIC_NAME": "expense-outcomes",
    "APPROVAL_TABLE_NAME": "ExpenseApprovals",
    "APPROVAL_TIMEOUT_MINUTES": "30"
  }
}
```

#### Step 5 — Implement the helper functions

A practical Version B project can include:

1. **submit_expense**  
   HTTP function that sends expense JSON into the Service Bus queue.  
   This makes your `test-expense.http` easy to use.

2. **validate_expense**  
   HTTP function called by the Logic App.  
   It checks required fields and category.

3. **manager decision helper**  
   Optional HTTP function if you choose to let a manager approve or reject manually.

If you use a table to store approval status, the helper can write a decision into that table.

#### Step 6 — Build the Logic App flow

Your Logic App should follow this order:

1. **Service Bus queue trigger**
   - Trigger when a message arrives in `expense-requests`

2. **Decode the message**
   - Service Bus messages often arrive encoded
   - Convert the payload to string
   - Parse the JSON

3. **Call the validation function**
   - Send the parsed expense request to `validate_expense`

4. **Handle validation errors**
   - If validation fails, send an error email or terminate with a clear failure path

5. **Branch on amount**
   - If `amount < 100`, auto-approve
   - If `amount >= 100`, enter the manager approval flow

6. **Manager approval flow**
   - Send the manager a notification
   - Wait using a polling loop or a delay-based loop
   - Stop when a decision is found
   - If no decision arrives before timeout, mark as escalated

7. **Send employee email**
   - Email the final result to the employee

8. **Publish outcome to the Service Bus topic**
   - Label the message as `approved`, `rejected`, or `escalated`

#### Step 7 — Create the email actions

Inside the Logic App:

- use one email action for approved results
- use one email action for rejected results
- use one email action for escalated results

Make the subject line and body include:

- employee name
- amount
- category
- description
- final decision
- any manager comments if applicable

#### Step 8 — Publish outcome messages

When the Logic App finishes processing, publish the result to `expense-outcomes` with the matching label.

That gives you a clean Service Bus topic routing setup with filtered subscriptions.

#### Step 9 — Create `test-expense.http`

Use this file to test the helper function that sends expense requests into the queue.

Include scenarios for:

1. valid expense under $100
2. valid expense >= $100 with manager approval
3. valid expense >= $100 with manager rejection
4. valid expense >= $100 with no manager response
5. missing required fields
6. invalid category

#### Step 10 — Capture screenshots

Save screenshots of:

- Service Bus queue and topic
- subscription filters
- Logic App run history
- validation success and failure
- approval and rejection branches
- timeout / escalation branch
- received emails

### 5.5 What to document in your README

For Version B, explain:

- why you picked your manager approval workaround
- how the Logic App decides the final outcome
- how Service Bus is used for decoupling
- how the subscriptions route the results

---

## 6. Comparison Analysis

Write a comparison of **800 to 1200 words** covering:

1. Development Experience
2. Testability
3. Error Handling
4. Human Interaction Pattern
5. Observability
6. Cost

### Suggested way to compare

Use specific examples from your build experience:

- what was faster to implement
- what was easier to debug in VS Code or Azure Portal
- which version made timeout handling easier
- which version gave clearer run history
- which version felt simpler for production scaling
- what you estimate at low and high usage

### Recommendation

End with a recommendation of **200 to 300 words** stating:

- which approach you would choose for production
- why you would choose it
- when the other approach would be a better fit

---

## 7. Presentation

Your presentation should include:

1. Introduction
2. Version A architecture and demo
3. Version B architecture and demo
4. Comparison summary
5. Recommendation
6. Lessons learned

Keep your screenshots and diagrams organized while you build, because they will save time when creating the slides.

---

## 8. AI Disclosure

Add a short disclosure section that says how AI was used, or state that no AI was used.

Example:

> AI was used to help organize the project structure, clarify Azure service choices, and draft documentation. All final code, testing, and deployment were completed and verified by me.

---

## 9. Suggested Build Order

Follow this order so you do not get stuck:

1. Build **Version A** first.
2. Test all six scenarios.
3. Deploy Version A.
4. Build **Version B** next.
5. Test all six scenarios.
6. Deploy Version B.
7. Write the comparison after both versions are working.
8. Build slides last.

This order helps because Version A teaches the orchestration logic, and Version B becomes easier once the workflow is already clear.

---

## 10. References

Add your final references here, including Azure documentation and any learning resources you used while building.

---

## 11. Notes

- Do not commit real secrets.
- Keep `local.settings.json` out of GitHub.
- Keep screenshots in the `screenshots/` folder for Version B.
- Make sure your README matches the code you actually submit.
