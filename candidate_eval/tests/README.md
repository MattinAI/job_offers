# Quick Start Guide: CV Analysis Platform Load Testing
A comprehensive load testing suite for the CV Analysis Platform using Locust to validate system performance under various load scenarios.

## 📋 Overview
This testing framework validates that the CV analysis system can handle:

- Primary Focus: PUT `/api/v1/job-offers/{job_offer_id}/candidates/{candidate_id}` (linking existing candidates).
- Secondary Focus: POST `/api/v1/job-offers/{job_offer_id}/candidates/` (creating and linking new candidates).
- Tertiary Focus: GET to various endpoints.

## 🏗️ Architecture
```
load-testing/
├── run_tests.sh             # Main test execution script
├── locustfile.py            # Locust test scenarios and user behaviors
├── data_prep.py             # Creates test data in database
├── test_data_ids.json       # Generated IDs for load testing
├── test_data/               # Test files
│   ├── cvs/                 # CV files (PDF, DOCX, TXT)
│   └── job_descriptions/    # Job description files
└── reports/                 # Generated test reports
    └── YYYYMMDD_HHMMSS/    # Timestamped report directories
```

## 🧪 How Locust Testing Works
### User Simulation Model
Locust simulates real users by creating virtual users that continuously perform tasks against your API:

```python
class MainEndpointTester(HttpUser):
    wait_time = between(4, 7)  # Each user waits 4-7 seconds between requests
```

### Task Weight System
Tasks use `@task(weight)` decorators where weight determines execution frequency:

```python
@task(2)  # Executes ~2x more often than weight 1
def put_link_existing_candidate_to_job(self):
    # Links existing candidate to job offer

@task(1)  # Base frequency
def post_create_and_link_candidate(self):
    # Creates new candidate and links to job offer
```

### Weight Distribution Example: Out of 6 total actions:

- `@task(2)` → Executes ~2 times (33%)
- `@task(1)` → Executes ~1 time each (17% each)

### User Class Weight System

Different user types are spawned based on class weights:

```python
class PutEndpointHeavyUser(MainEndpointTester):
    weight = 3  # 30% of users (3 out of 10 total weight)

class BalancedUser(MainEndpointTester):
    weight = 4  # 40% of users (4 out of 10 total weight)
```

### Task Inheritance
Specialized user classes inherit ALL tasks from the parent class AND add their own:

- `MainEndpointTester` has 6 base tasks (weights 1-2)
- `PutEndpointHeavyUser` inherits these 6 tasks + adds 2 specialized tasks (weights 10, 2)
- Result: 8 total tasks in pool, but specialized tasks dominate due to higher weights

## 👥 User Types & Behaviors

### 1. MainEndpointTester (Base Class)

`Weight`: 1 (implicit) | `Focus`: Balanced testing
```python
@task(2) PUT endpoint  # Primary endpoint
@task(1) POST endpoint # Secondary endpoint  
@task(1) GET validation endpoints (3 different)
```

### 2. PutEndpointHeavyUser

`Weight`: 3 | `Focus`: PUT endpoint intensive testing
```python
@task(10) intensive_put_linking()    # Dominates execution
@task(2)  validation_check()         # Monitors results
# + inherits all 6 base tasks
```

### 3. PostEndpointHeavyUser
`Weight`: 2 | `Focus`: POST endpoint intensive testing
```python
@task(10) intensive_post_creation()  # Dominates execution
@task(3)  validation_check()         # Monitors results
# + inherits all 6 base tasks
```

### 4. BalancedUser
`Weight`: 4 | `Focus`: Equal PUT/POST usage
```python
@task(8) balanced_put()      # 2:1 ratio PUT to POST
@task(4) balanced_post()     
@task(2) monitor_results()   
# + inherits all 6 base tasks
```

### 5. MonitoringUser
`Weight`: 1 | `Focus`: GET operations only
```python
@task(5) monitor_job_candidates()    # Primary monitoring
@task(3) monitor_all_candidates()    # Secondary monitoring  
@task(2) monitor_job_offers()        # Light monitoring
# Slower wait_time = between(2, 5)
```

## 🎯 API Endpoints Tested
| Endpoint                                         | Method | Purpose               | Primary User     | Weight   |
|--------------------------------------------------|--------|------------------------|------------------|----------|
| `/api/v1/job-offers/{id}/candidates/{id}`        | PUT    | Link existing candidate | PutEndpointHeavyUser | High     |
| `/api/v1/job-offers/{id}/candidates/`            | POST   | Create & link candidate | PostEndpointHeavyUser | High     |
| `/api/v1/job-offers/{id}/candidates/`            | GET    | Get job candidates      | All users           | Medium   |
| `/api/v1/candidates/`                            | GET    | List all candidates     | MonitoringUser       | Low      |
| `/api/v1/job-offers/`                            | GET    | List all job offers     | MonitoringUser       | Low      |

## 🚀 Getting Started

### Step 1: Prepare Test Data
The data preparation pipeline creates job offers and candidates in your database:
```bash
# Create test data (10 job offers, 100 candidates)
python data_prep.py --job-offers 10 --candidates 10 --api-url http://localhost:8000
```

### What it does:

1. Cycles through your CV files to create multiple candidates
2. Cycles through job description files to create multiple job offers
3. Saves all created IDs to test_data_ids.json
4. Validates each candidate exists before adding to test pool

### Step 2: Run Load Tests
Make the test script executable and run:

```bash
chmod +x run_tests.sh

# Run specific test scenario
./run_tests.sh --test peak_endpoint_validation --api-url http://localhost:8000
```

--------------
## 🧪 Test Scenarios

### Test Parameters Explained

`Duration`: How long the test runs continuously

- 10m = 10 minutes of sustained load testing
- 30m = 30 minutes for comprehensive validation

`Users`: Maximum concurrent users hitting your API simultaneously

- 10 users = 10 people using the system at the same time
- 100 users = 100 people uploading CVs and matching jobs concurrently

`Spawn Rate`: How fast users join the test (ramp-up speed)

- 2 users/second = Every second, 2 new users start until reaching max users
- 10 users/second = Faster ramp-up to peak load

`Example`: Peak Load Test (100 users, 10/second spawn, 30 minutes)

- Seconds 1-10: Ramps from 0 → 100 users (10 added each second)
- Minutes 1-30: All 100 users continuously test your API
- Each user randomly performs weighted tasks throughout the duration

| Test Name              | Users | Duration | Spawn Rate | Focus                  |
|------------------------|-------|----------|------------|-------------------------|
| `light_endpoint`       | 10    | 3 min    | 1/sec      | Basic validation        |
| `moderate_endpoint`    | 25    | 5 min    | 1/sec      | Moderate load           |
| `heavy_put`            | 50    | 8 min    | 1/sec      | PUT endpoint stress     |
| `balanced_endpoint`    | 75    | 10 min   | 1/sec     | Both endpoints equally  |
| `peak_endpoint_validation` | 100   | 15 min  | 1/sec     | Primary validation       |

### Test Execution Flow

#### Example: Peak Load Test (100 users, 15/sec spawn, 15 minutes)

1. Ramp-up Phase (0-7 seconds):

15 new users join each second until reaching 100 total users

2. Sustained Load Phase (7 seconds - 15 minutes):

- All 100 users continuously execute tasks
- Each user randomly selects tasks based on their class weights
- Users wait 4-7 seconds between requests

3. User Distribution (based on class weights):

- ~40 BalancedUsers (weight 4)
- ~30 PutEndpointHeavyUsers (weight 3)
- ~20 PostEndpointHeavyUsers (weight 2)
- ~10 MonitoringUsers (weight 1)                                   |

