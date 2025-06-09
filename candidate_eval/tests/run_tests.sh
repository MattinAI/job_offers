#!/bin/bash

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
API_URL=${API_URL:-"http://localhost:8000"}
REPORT_DIR="reports/focused_$(date +%Y%m%d_%H%M%S)"
GRACEFUL_SHUTDOWN_TIME=${GRACEFUL_SHUTDOWN_TIME:-"1m"}

echo -e "${GREEN}🎯 Focused CV Analysis Platform Load Testing${NC}"
echo "=============================================="
echo -e "${BLUE}Primary Focus: PUT /api/v1/job-offers/{job_offer_id}/candidates/{candidate_id}${NC}"
echo -e "${BLUE}Secondary Focus: POST /api/v1/job-offers/{job_offer_id}/candidates/${NC}"

# Create reports directory
mkdir -p "$REPORT_DIR"

# Function to convert duration string to seconds
duration_to_seconds() {
    local duration=$1
    local seconds=0
    
    if [[ $duration =~ ([0-9]+)m ]]; then
        seconds=$((${BASH_REMATCH[1]} * 60))
    elif [[ $duration =~ ([0-9]+)s ]]; then
        seconds=${BASH_REMATCH[1]}
    elif [[ $duration =~ ([0-9]+)h ]]; then
        seconds=$((${BASH_REMATCH[1]} * 3600))
    fi
    
    echo $seconds
}

# Function to check if test data exists
check_test_data() {
    echo -e "\n${YELLOW}🔍 Checking Test Data${NC}"
    
    if [ ! -f "test_data_ids.json" ]; then
        echo -e "${RED}❌ test_data_ids.json not found!${NC}"
        echo "Please run the data preparation pipeline first:"
        echo "  python data_preparation_pipeline.py --job-offers 10 --candidates 100"
        return 1
    fi
    
    # Validate JSON and extract counts
    python3 << 'EOF'
import json
import sys

try:
    with open('test_data_ids.json', 'r') as f:
        data = json.load(f)
    
    job_offers = len(data.get('job_offers', []))
    candidates = len(data.get('candidates', []))
    
    print(f"✅ Test data found:")
    print(f"   Job Offers: {job_offers}")
    print(f"   Candidates: {candidates}")
    
    if job_offers == 0:
        print("❌ No job offers in test data!")
        sys.exit(1)
    
    if candidates == 0:
        print("❌ No candidates in test data!")
        sys.exit(1)
    
    if job_offers < 5:
        print("⚠️ Fewer than 5 job offers - consider creating more for better testing")
    
    if candidates < 50:
        print("⚠️ Fewer than 50 candidates - consider creating more for better testing")
    
    print(f"🎯 Ready for focused endpoint testing!")
    
except Exception as e:
    print(f"❌ Error reading test data: {e}")
    sys.exit(1)
EOF
    
    return $?
}

# Function to check API health
check_api_health() {
    echo -e "\n${YELLOW}🔍 Checking API Health${NC}"
    
    # Basic connectivity check
    if ! curl -f -s --max-time 10 "$API_URL/api/v1/job-offers/" > /dev/null 2>&1; then
        echo -e "${RED}❌ API not accessible at $API_URL${NC}"
        echo "Please ensure your API is running"
        return 1
    fi
    
    echo -e "${GREEN}✅ API accessible at $API_URL${NC}"
    
    # Check if we can access our test data
    echo "🔍 Validating test data accessibility..."
    
    python3 << 'EOF'
import json
import requests
import sys
import os

api_url = os.environ.get('API_URL', 'http://localhost:8000')

try:
    with open('test_data_ids.json', 'r') as f:
        data = json.load(f)
    
    # Test accessing first job offer and candidate
    if data['job_offers']:
        first_job_id = data['job_offers'][0]['id']
        response = requests.get(f"{api_url}/api/v1/job-offers/{first_job_id}/candidates/", timeout=10)
        if response.status_code == 200:
            print(f"✅ Can access job offer {first_job_id}")
        else:
            print(f"⚠️ Job offer {first_job_id} returned {response.status_code}")
    
    if data['candidates'] and len(data['candidates']) > 0:
        candidate_count = len(data['candidates'])
        print(f"✅ {candidate_count} candidates available for testing")
    
    print("🎯 Test data is accessible via API")
    
except Exception as e:
    print(f"❌ Error validating test data: {e}")
    sys.exit(1)
EOF
    
    return $?
}

# Function to run focused test
run_focused_test() {
    local test_name=$1
    local users=$2
    local spawn_rate=$3
    local run_time=$4
    local description=$5
    
    echo -e "\n${YELLOW}📊 Running Focused Test: $test_name${NC}"
    echo "Description: $description"
    echo "Users: $users, Spawn Rate: $spawn_rate, Duration: $run_time"
    echo "Target URL: $API_URL"
    
    # Create test-specific report directory
    local test_report_dir="$REPORT_DIR/$test_name"
    mkdir -p "$test_report_dir"
    
    echo -e "${BLUE}Starting focused endpoint testing...${NC}"
    
    # Create Locust configuration
    cat > "$test_report_dir/locust.conf" << EOF
# Locust configuration for $test_name
host = $API_URL
users = $users
spawn-rate = $spawn_rate
run-time = $run_time
headless = true
csv = $test_report_dir/results
html = $test_report_dir/report.html
logfile = $test_report_dir/locust.log
loglevel = INFO
locustfile = locustfile.py
EOF
    
    # Run Locust test
    if ! locust --config "$test_report_dir/locust.conf"; then
        echo -e "${RED}❌ Test failed${NC}"
        return 1
    fi
    
    echo -e "${GREEN}✅ Test $test_name completed${NC}"
    echo "Reports saved to: $test_report_dir"
    
    # Generate immediate test summary
    generate_focused_summary "$test_report_dir" "$test_name"
}

# Function to generate focused test summary
generate_focused_summary() {
    local test_dir=$1
    local test_name=$2
    
    if [ -f "$test_dir/results_stats.csv" ]; then
        echo -e "\n${BLUE}📈 Focused Test Summary for $test_name:${NC}"
        
        python3 << EOF
import csv
import os

stats_file = "$test_dir/results_stats.csv"
if os.path.exists(stats_file):
    with open(stats_file, 'r') as f:
        reader = csv.DictReader(f)
        
        total_requests = 0
        total_failures = 0
        put_requests = 0
        put_failures = 0
        post_requests = 0
        post_failures = 0
        get_requests = 0
        get_failures = 0
        
        put_avg_time = 0
        post_avg_time = 0
        overall_avg_time = 0
        throughput = 0
        
        for row in reader:
            requests = int(row['Request Count'])
            failures = int(row['Failure Count'])
            avg_time = float(row['Average Response Time'])
            
            if row['Type'] == 'Aggregated':
                total_requests = requests
                total_failures = failures
                overall_avg_time = avg_time
                throughput = float(row['Requests/s'])
                
            elif 'PUT Link Existing Candidate' in row['Name']:
                put_requests = requests
                put_failures = failures
                put_avg_time = avg_time
                
            elif 'POST Create and Link Candidate' in row['Name']:
                post_requests = requests
                post_failures = failures
                post_avg_time = avg_time
                
            elif 'GET' in row['Name']:
                get_requests += requests
                get_failures += failures
        
        # Calculate rates
        overall_failure_rate = (total_failures / max(total_requests, 1)) * 100
        put_failure_rate = (put_failures / max(put_requests, 1)) * 100
        post_failure_rate = (post_failures / max(post_requests, 1)) * 100
        get_failure_rate = (get_failures / max(get_requests, 1)) * 100
        
        print(f"📊 OVERALL METRICS:")
        print(f"   Total Requests: {total_requests:,}")
        print(f"   Total Failures: {total_failures:,} ({overall_failure_rate:.2f}%)")
        print(f"   Avg Response Time: {overall_avg_time:.0f}ms")
        print(f"   Throughput: {throughput:.2f} req/s")
        
        print(f"\\n🎯 PUT ENDPOINT (Primary Focus):")
        print(f"   Requests: {put_requests:,}")
        print(f"   Failures: {put_failures:,} ({put_failure_rate:.2f}%)")
        print(f"   Avg Response Time: {put_avg_time:.0f}ms")
        
        print(f"\\n📝 POST ENDPOINT (Secondary Focus):")
        print(f"   Requests: {post_requests:,}")
        print(f"   Failures: {post_failures:,} ({post_failure_rate:.2f}%)")
        print(f"   Avg Response Time: {post_avg_time:.0f}ms")
        
        print(f"\\n👁️ GET ENDPOINTS (Monitoring):")
        print(f"   Requests: {get_requests:,}")
        print(f"   Failures: {get_failures:,} ({get_failure_rate:.2f}%)")
        
        # Performance assessment
        print(f"\\n🏆 PERFORMANCE ASSESSMENT:")
        
        issues = []
        if put_failure_rate > 2.0:
            issues.append(f"High PUT failure rate: {put_failure_rate:.2f}%")
        if post_failure_rate > 5.0:
            issues.append(f"High POST failure rate: {post_failure_rate:.2f}%")
        if put_avg_time > 10000:
            issues.append(f"Slow PUT response: {put_avg_time:.0f}ms")
        if post_avg_time > 20000:
            issues.append(f"Slow POST response: {post_avg_time:.0f}ms")
        
        if not issues:
            print("   ✅ All endpoints performing well!")
        else:
            print("   ⚠️ Issues detected:")
            for issue in issues:
                print(f"      - {issue}")
        
        # Endpoint ratio analysis
        if total_requests > 0:
            put_ratio = (put_requests / total_requests) * 100
            post_ratio = (post_requests / total_requests) * 100
            get_ratio = (get_requests / total_requests) * 100
            
            print(f"\\n📈 REQUEST DISTRIBUTION:")
            print(f"   PUT requests: {put_ratio:.1f}%")
            print(f"   POST requests: {post_ratio:.1f}%")
            print(f"   GET requests: {get_ratio:.1f}%")
EOF
    fi
}

# Function to generate comprehensive summary
generate_comprehensive_summary() {
    echo -e "\n${YELLOW}📈 Generating Comprehensive Summary${NC}"
    
    python3 << 'EOF'
import os
import json
import csv
from pathlib import Path
from datetime import datetime

report_dir = Path(os.environ.get('REPORT_DIR', '.'))
summary_data = []

# Aggregate metrics across all tests
total_put_requests = 0
total_put_failures = 0
total_post_requests = 0
total_post_failures = 0
total_requests = 0
total_failures = 0

put_response_times = []
post_response_times = []

# Process each test result
for test_dir in report_dir.iterdir():
    if test_dir.is_dir():
        stats_file = test_dir / "results_stats.csv"
        if stats_file.exists():
            test_put_reqs = 0
            test_put_fails = 0
            test_post_reqs = 0
            test_post_fails = 0
            test_total_reqs = 0
            test_total_fails = 0
            
            with open(stats_file, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    requests = int(row['Request Count'])
                    failures = int(row['Failure Count'])
                    avg_time = float(row['Average Response Time'])
                    
                    if row['Type'] == 'Aggregated':
                        test_total_reqs = requests
                        test_total_fails = failures
                        
                    elif 'PUT Link Existing Candidate' in row['Name']:
                        test_put_reqs = requests
                        test_put_fails = failures
                        if avg_time > 0:
                            put_response_times.append(avg_time)
                            
                    elif 'POST Create and Link Candidate' in row['Name']:
                        test_post_reqs = requests
                        test_post_fails = failures
                        if avg_time > 0:
                            post_response_times.append(avg_time)
            
            # Add to totals
            total_put_requests += test_put_reqs
            total_put_failures += test_put_fails
            total_post_requests += test_post_reqs
            total_post_failures += test_post_fails
            total_requests += test_total_reqs
            total_failures += test_total_fails
            
            # Store test data
            summary_data.append({
                'test_name': test_dir.name,
                'total_requests': test_total_reqs,
                'total_failures': test_total_fails,
                'put_requests': test_put_reqs,
                'put_failures': test_put_fails,
                'post_requests': test_post_reqs,
                'post_failures': test_post_fails
            })

# Calculate overall metrics
overall_failure_rate = (total_failures / max(total_requests, 1)) * 100
put_failure_rate = (total_put_failures / max(total_put_requests, 1)) * 100
post_failure_rate = (total_post_failures / max(total_post_requests, 1)) * 100

avg_put_time = sum(put_response_times) / len(put_response_times) if put_response_times else 0
avg_post_time = sum(post_response_times) / len(post_response_times) if post_response_times else 0

# Determine final validation status
validation_status = {
    'endpoints_validated': True,
    'put_endpoint_grade': 'PASS' if put_failure_rate < 2.0 and avg_put_time < 10000 else 'FAIL',
    'post_endpoint_grade': 'PASS' if post_failure_rate < 5.0 and avg_post_time < 20000 else 'FAIL',
    'overall_grade': 'PASS',
    'issues': []
}

# Check for issues
if put_failure_rate >= 2.0:
    validation_status['issues'].append(f"PUT failure rate too high: {put_failure_rate:.2f}%")
if post_failure_rate >= 5.0:
    validation_status['issues'].append(f"POST failure rate too high: {post_failure_rate:.2f}%")
if avg_put_time >= 10000:
    validation_status['issues'].append(f"PUT response time too slow: {avg_put_time:.0f}ms")
if avg_post_time >= 20000:
    validation_status['issues'].append(f"POST response time too slow: {avg_post_time:.0f}ms")

if validation_status['issues']:
    validation_status['overall_grade'] = 'FAIL'

# Generate final summary
final_summary = {
    'generated_at': datetime.now().isoformat(),
    'total_tests': len(summary_data),
    'endpoint_metrics': {
        'put_endpoint': {
            'total_requests': total_put_requests,
            'total_failures': total_put_failures,
            'failure_rate': put_failure_rate,
            'avg_response_time': avg_put_time
        },
        'post_endpoint': {
            'total_requests': total_post_requests,
            'total_failures': total_post_failures,
            'failure_rate': post_failure_rate,
            'avg_response_time': avg_post_time
        },
        'overall': {
            'total_requests': total_requests,
            'total_failures': total_failures,
            'failure_rate': overall_failure_rate
        }
    },
    'validation_status': validation_status,
    'test_results': summary_data
}

# Save summary
summary_file = report_dir / "focused_test_summary.json"
with open(summary_file, 'w') as f:
    json.dump(final_summary, f, indent=2)

print(f"📊 Comprehensive summary saved to: {summary_file}")
print(f"\\n🎯 FINAL FOCUSED TEST RESULTS:")
print(f"PUT Endpoint: {total_put_requests:,} requests, {put_failure_rate:.2f}% failures, {avg_put_time:.0f}ms avg")
print(f"POST Endpoint: {total_post_requests:,} requests, {post_failure_rate:.2f}% failures, {avg_post_time:.0f}ms avg")

EOF

    export REPORT_DIR="$REPORT_DIR"
}

# Main execution function
main() {
    echo -e "\n${GREEN}🎯 Starting Focused Endpoint Testing${NC}"
    echo "Report Directory: $REPORT_DIR"
    
    # Check test data
    if ! check_test_data; then
        exit 1
    fi
    
    # Check API health
    if ! check_api_health; then
        exit 1
    fi
    
    # Check if focused_load_test.py exists
    if [ ! -f "locustfile.py" ]; then
        echo -e "${RED}❌ locustfile.py not found!${NC}"
        echo "Please ensure the focused load test file is in the current directory"
        exit 1
    fi
    
    echo -e "\n${BLUE}🚀 Running Focused Test Suite${NC}"
    echo "Primary: PUT /api/v1/job-offers/{job_offer_id}/candidates/{candidate_id}"
    echo "Secondary: POST /api/v1/job-offers/{job_offer_id}/candidates/"
    
    # Test scenarios focused on the main endpoints
    
    # Light load test
    run_focused_test "light_endpoint_test" 10 2 "3m" "Light load - 10 users testing both endpoints"
    
    # Moderate load test  
    run_focused_test "moderate_endpoint_test" 25 5 "5m" "Moderate load - 25 users with balanced endpoint usage"
    
    # Heavy PUT focus test
    run_focused_test "heavy_put_test" 50 8 "8m" "Heavy PUT endpoint testing - 50 users"
    
    # Balanced endpoint test
    run_focused_test "balanced_endpoint_test" 75 10 "10m" "Balanced testing of both endpoints - 75 users"
    
    # Peak validation test
    echo -e "\n${RED}🚨 PEAK ENDPOINT VALIDATION${NC}"
    echo "Testing the main requirement: 100 users using both endpoints intensively"
    run_focused_test "peak_endpoint_validation" 100 15 "15m" "Peak validation - 100 users, intensive endpoint testing"
    
    # Generate comprehensive summary
    generate_comprehensive_summary
    
    echo -e "\n${GREEN}🎉 Focused endpoint testing completed!${NC}"
    echo -e "📁 Reports available in: ${YELLOW}$REPORT_DIR${NC}"
    echo -e "📊 Summary: ${YELLOW}$REPORT_DIR/focused_test_summary.json${NC}"
    
    # Display final results
    if [ -f "$REPORT_DIR/focused_test_summary.json" ]; then
        echo -e "\n${BLUE}🏆 FINAL ENDPOINT VALIDATION:${NC}"
        python3 -c "
import json
with open('$REPORT_DIR/focused_test_summary.json', 'r') as f:
    data = json.load(f)

put_metrics = data['endpoint_metrics']['put_endpoint']
post_metrics = data['endpoint_metrics']['post_endpoint']
status = data['validation_status']

print(f\"PUT Endpoint Grade: {status['put_endpoint_grade']}\")
print(f\"POST Endpoint Grade: {status['post_endpoint_grade']}\")
print(f\"Overall Grade: {status['overall_grade']}\")
print(f\"\\nPUT: {put_metrics['total_requests']:,} reqs, {put_metrics['failure_rate']:.2f}% fails, {put_metrics['avg_response_time']:.0f}ms\")
print(f\"POST: {post_metrics['total_requests']:,} reqs, {post_metrics['failure_rate']:.2f}% fails, {post_metrics['avg_response_time']:.0f}ms\")

if status['issues']:
    print('\\n⚠️ Issues:')
    for issue in status['issues']:
        print(f'  - {issue}')
else:
    print('\\n✅ Both endpoints performing within acceptable limits!')
"
    fi
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --api-url=*)
            API_URL="${1#*=}"
            shift
            ;;
        --api-url)
            API_URL="$2"
            shift 2
            ;;
        --test=*)
            TEST_TYPE="${1#*=}"
            shift
            ;;
        --test)
            TEST_TYPE="$2"
            shift 2
            ;;
        --help)
            echo "Focused CV Analysis Endpoint Testing"
            echo "Tests PUT and POST endpoints using pre-created data"
            echo
            echo "Usage: $0 [OPTIONS]"
            echo
            echo "Prerequisites:"
            echo "  1. Run data preparation first:"
            echo "     python data_preparation_pipeline.py --job-offers 10 --candidates 100"
            echo "  2. Ensure locustfile.py is in current directory"
            echo
            echo "Options:"
            echo "  --api-url=URL    API base URL (default: http://localhost:8000)"
            echo "  --test=TYPE      Run specific test scenario"
            echo "  --help           Show this help message"
            echo
            echo "Available test types:"
            echo "  light_endpoint     - 10 users, 3 minutes"
            echo "  moderate_endpoint  - 25 users, 5 minutes"
            echo "  heavy_put         - 50 users, 8 minutes (PUT focus)"
            echo "  balanced_endpoint - 75 users, 10 minutes"
            echo "  peak_endpoint_validation - 100 users, 15 minutes"
            echo
            echo "Example:"
            echo "  $0                           # Run all tests"
            echo "  $0 --test=peak_endpoint_validation  # Run main validation only"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Export environment variables
export API_URL
export REPORT_DIR

# Run specific test or all tests
if [[ -n "$TEST_TYPE" ]]; then
    # Check prerequisites
    if ! check_test_data; then
        exit 1
    fi
    if ! check_api_health; then
        exit 1
    fi
    
    case $TEST_TYPE in
        light_endpoint)
            run_focused_test "light_endpoint_test" 10 1 "3m" "Light endpoint test"
            ;;
        moderate_endpoint)
            run_focused_test "moderate_endpoint_test" 25 1 "5m" "Moderate endpoint test"
            ;;
        heavy_put)
            run_focused_test "heavy_put_test" 50 1 "8m" "Heavy PUT endpoint test"
            ;;
        balanced_endpoint)
            run_focused_test "balanced_endpoint_test" 75 1 "10m" "Balanced endpoint test"
            ;;
        peak_endpoint_validation)
            echo -e "\n${RED}🚨 PEAK ENDPOINT VALIDATION${NC}"
            run_focused_test "peak_endpoint_validation" 100 1 "10m" "Peak endpoint validation"
            ;;
        *)
            echo -e "${RED}❌ Unknown test type: $TEST_TYPE${NC}"
            echo "Available: light_endpoint, moderate_endpoint, heavy_put, balanced_endpoint, peak_endpoint_validation"
            exit 1
            ;;
    esac
    
    generate_comprehensive_summary
else
    main
fi