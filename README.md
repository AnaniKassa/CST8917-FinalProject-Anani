# CST8917 Final Project — Compare & Contrast: Expense Approval Workflow

**Course:** CST8917 — Serverless Applications  
**Project:** Dual implementation of an Expense Approval Workflow  
**Student:** Anani Thierry Kassa  
**Student Number:** 041140713  
**Date:** 2026-04-21

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
#### Step 3 — Implement the function roles

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

#### Step 4 — Build the orchestrator logic

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

#### Step 5 — Add the manager response endpoint

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

#### Step 6 — Test locally with `test-durable.http`

Create `version-a-durable-functions/test-durable.http` with test cases for:

1. Expense under $100 → auto-approved
2. Expense >= $100 with manager approval
3. Expense >= $100 with manager rejection
4. Expense >= $100 with no response before timeout
5. Missing required fields
6. Invalid category

For the approval/rejection cases, first start the orchestration, then call the manager response endpoint with the returned instance ID.

#### Step 7 — Run Azurite and start the app

1. Start **Azurite**.
2. Run the function app locally in VS Code.
3. Confirm the endpoints appear in the terminal.
4. Run your HTTP tests.

#### Step 8 — Deploy to Azure

1. Create a **Function App** in Azure.
2. Use the same runtime and region as your storage account.
3. Add the production app settings.
4. Deploy from VS Code.
5. Retest all scenarios in Azure.

### 4.4 Challenges
The main challenge in Version A is correctly implementing the **Human Interaction pattern** with Durable Functions. You need to manage timers and external events carefully to avoid issues like orphaned timers or missed events. Testing this flow locally can also be tricky, especially simulating the manager response and ensuring the orchestration reacts correctly to timeouts.

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


#### Step 4 — Implement the helper functions

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

#### Step 5 — Build the Logic App flow

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

#### Step 6 — Create the email actions

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

#### Step 7 — Publish outcome messages

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

#### Step 8 — Challenge
  
Had hard time setting up the manager approval flow in Logic Apps. The polling loop approach is not ideal but it’s a practical workaround to demonstrate waiting for human input without Durable Functions.

---

## 6. Comparison Analysis (Full 800-1200 word comparison)

This project compares two approaches for building an expense approval workflow: Version A using Azure Durable Functions and Version B using Azure Logic Apps with Service Bus. Both solutions achieve the same functional goal—processing expense requests, validating inputs, handling approvals, and notifying users—but they differ significantly in architecture, complexity, and maintainability.

**Architecture and Design**

Durable Functions follows a code-first architecture, where the entire workflow is defined programmatically using an orchestrator function and multiple activity functions. The orchestrator acts as the central controller, coordinating each step in a clear and structured manner. This results in a single, cohesive workflow that is easy to follow and reason about.

In contrast, Logic Apps with Service Bus uses a low-code, event-driven architecture. The workflow is visually designed using triggers, conditions, and actions. Service Bus introduces a messaging layer that decouples components. Instead of one central orchestrator, the logic is distributed across multiple steps and services, making the system more modular but also more complex to track.

**Orchestration and Workflow Control**

One of the biggest differences lies in orchestration.

Durable Functions provides built-in orchestration capabilities, allowing the system to:

- Wait for external events (e.g., manager approval)
- Handle timeouts natively
- Maintain execution state automatically

This makes implementing workflows with delays or human interaction straightforward. For example, waiting for a manager’s decision or escalating after a timeout can be handled cleanly within the orchestrator.

Logic Apps, on the other hand, requires manual orchestration. Developers must combine conditions, delays, and variables to simulate workflow behavior. While this works, it is less intuitive and can lead to errors. For example, simulating a manager approval step required using a delay and conditional logic rather than a true event-based mechanism.

**State Management**

State management is another key differentiator.

Durable Functions automatically manages state between steps. The orchestration context preserves data across executions, making it ideal for long-running workflows.

Logic Apps requires explicit state handling. Variables must be initialized and updated manually, or external storage (such as tables) must be used. This increases complexity and introduces potential issues if not handled carefully.

**Scalability and Decoupling**

Logic Apps combined with Service Bus offers strong decoupling and scalability.

- Service Bus queues allow asynchronous processing of incoming requests
- Topics and subscriptions enable routing of outcomes (approved, rejected, escalated)
- Components can scale independently

This makes Version B more suitable for distributed systems and enterprise-scale applications.

Durable Functions also scales, but it is more tightly coupled, as all logic resides within the orchestrator. While this simplifies development, it reduces flexibility in highly distributed architectures.
  
**Development Experience**
  
Durable Functions provides a developer-friendly experience, especially for those comfortable with programming. Writing logic in Python allows better control, easier debugging, and cleaner version management.

Logic Apps offers a visual, low-code experience, which is easier for beginners or non-developers. However, as workflows grow more complex, the visual design can become cluttered, and managing expressions or data transformations can be challenging.
  
**Integration Capabilities**
  
Logic Apps has a clear advantage in integration. It provides built-in connectors for services such as email, HTTP APIs, and messaging systems. This allows rapid development without writing much code.

Durable Functions requires manual integration using SDKs or API calls. While more flexible, it increases development effort.
  
**Error Handling and Debugging**
  
Durable Functions offers structured logging and a clear execution flow within the orchestrator, making debugging more straightforward.

Logic Apps provides a visual run history, which is helpful, but debugging can become difficult when workflows contain many nested conditions and actions. Errors such as invalid JSON or incorrect expressions are common and sometimes harder to trace.
  
**Cost and Maintainability**

Durable Functions generally has a lower cost for compute-based workflows, as billing is based on execution time.

Logic Apps uses a per-action pricing model, which can become expensive as the number of steps increases. Service Bus also adds additional cost.

In terms of maintainability, Durable Functions is easier to manage for developers due to structured code and clear logic. Logic Apps can become harder to maintain over time due to visual complexity and scattered logic.
  
**Conclusion**

Both approaches have strengths, but they serve different purposes. Durable Functions is better suited for workflows that require strong orchestration, state management, and developer control. Logic Apps with Service Bus is more appropriate for integration-heavy, distributed systems where decoupling and scalability are priorities.

---

## 7.Recommendation (200-300 word recommendation)
  
Based on the comparison, Azure Durable Functions is the recommended approach for this expense approval system, especially in scenarios requiring structured workflows, state management, and reliability.
  
Durable Functions provides a cleaner and more maintainable solution by handling orchestration, state persistence, and event waiting natively. The ability to wait for external events (such as manager approval) and handle timeouts in a straightforward manner significantly reduces complexity and potential errors. This makes it ideal for workflows that involve multiple steps and decision points.
  
While Logic Apps combined with Service Bus offers strong integration capabilities and better decoupling, it introduces additional complexity in workflow design and state handling. The need to manually simulate approval logic and manage variables makes the solution harder to debug and maintain. Additionally, the cost model based on action execution may become less efficient as the workflow grows.
  
However, Logic Apps remains a strong choice for integration-heavy environments or when working with teams that prefer low-code solutions.
  
In conclusion, for this project’s requirements—especially the need for controlled orchestration and timeout handling—Durable Functions offers a more robust, scalable, and developer-friendly solution.
  
---

## 8. References

- Assignment lab 2 : https://github.com/AnaniKassa/26W_CST8917_Lab2/blob/main/README.md
- Assignment lab 3 : https://github.com/AnaniKassa/26W_CST8917_Lab3/blob/main/README.md

---

## 9. AI Disclosure

> Artificial Intelligence tools were used in a limited and supportive capacity during the completion of this project. Specifically, AI assistance was leveraged to help clarify technical concepts, troubleshoot errors during development (such as Azure Functions configuration and Logic Apps expressions), and improve the clarity and structure of written sections of the report.

> All architectural decisions, implementation steps, and testing processes were performed and validated independently. The code for both Version A (Azure Durable Functions) and Version B (Azure Logic Apps with Service Bus), as well as the overall system design, were developed, tested, and refined by the author. AI-generated suggestions were reviewed critically and adapted as needed to fit the project requirements.

> AI was not used to automatically generate the entire solution or replace understanding of the material. Instead, it served as a learning aid and productivity tool, similar to documentation or online resources.

> This ensures that the final submission reflects the author’s own understanding, work, and implementation of the project.
