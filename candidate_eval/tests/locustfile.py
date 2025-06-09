# locustfile.py - Focused Load Testing for Main Endpoints
import os
import json
import random
import time
from pathlib import Path
from typing import List, Dict, Any
from io import BytesIO

from locust import HttpUser, task, between, events
import requests

class MainEndpointTester(HttpUser):
    """
    Focused load tester for the two main endpoints:
    - PUT /api/v1/job-offers/{job_offer_id}/candidates/{candidate_id}
    - POST /api/v1/job-offers/{job_offer_id}/candidates/
    """
    wait_time = between(4, 7)
    _data_loaded = False
    _data_load_lock = None
    
    def on_start(self):
        """Load pre-created data IDs and test files"""
        import threading
        if MainEndpointTester._data_load_lock is None:
            MainEndpointTester._data_load_lock = threading.Lock()
            
        with MainEndpointTester._data_load_lock:
            if not MainEndpointTester._data_loaded:
                self.load_test_data()
                # Verify candidates AFTER loading
                valid_candidates = []
                for cid in self.candidate_ids:
                    response = self.client.get(f"/api/v1/candidates/{cid}")
                    if response.status_code == 200:
                        valid_candidates.append(cid)
                self.candidate_ids = valid_candidates
                MainEndpointTester._candidate_ids = valid_candidates
                MainEndpointTester._data_loaded = True
            else:
                # Just assign the already loaded data
                self.job_offer_ids = MainEndpointTester._job_offer_ids
                self.candidate_ids = MainEndpointTester._candidate_ids
                print(f"👤 New user added")
        
        self.load_test_files()
        
    def load_test_data(self):
        """Load pre-created job offers and candidates from JSON file"""
        try:
            with open('test_data_ids.json', 'r') as f:
                data = json.load(f)
            
            MainEndpointTester._job_offer_ids = [jo['id'] for jo in data['job_offers']]
            MainEndpointTester._candidate_ids = [c['id'] for c in data['candidates']]
            
            self.job_offer_ids = MainEndpointTester._job_offer_ids
            self.candidate_ids = MainEndpointTester._candidate_ids
            
            print(f"👤 New user added ({len(self.job_offer_ids)} job offers, {len(self.candidate_ids)} candidates available)")
            
            if not self.job_offer_ids:
                raise Exception("No job offers found in test data!")
            if not self.candidate_ids:
                raise Exception("No candidates found in test data!")
                
        except FileNotFoundError:
            raise Exception(
                "test_data_ids.json not found! Please run the data preparation pipeline first:\n"
                "python data_preparation_pipeline.py"
            )
        except Exception as e:
            raise Exception(f"Failed to load test data: {e}")
        
    def load_test_files(self):
        """Load test files for POST endpoint (creating new candidates)"""
        self.test_files = {"cvs": []}
        
        cv_path = Path("test_data/cvs")
        if cv_path.exists():
            for ext in ["*.pdf", "*.docx", "*.txt"]:
                self.test_files["cvs"].extend([str(f) for f in cv_path.glob(ext)])
        
        if not self.test_files["cvs"]:
            print("⚠️ No CV files found for POST endpoint testing")
    
    def get_content_type(self, filename: str) -> str:
        """Get content type based on file extension"""
        ext = Path(filename).suffix.lower()
        content_types = {
            '.pdf': 'application/pdf',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.doc': 'application/msword',
            '.txt': 'text/plain'
        }
        return content_types.get(ext, 'application/octet-stream')
    
    def get_cv_file_content(self) -> tuple[bytes, str, str]:
        """Get random CV file content for POST requests"""
        if not self.test_files["cvs"]:
            raise Exception("No CV files available for testing!")
        
        cv_path = random.choice(self.test_files["cvs"])
        
        # Create unique filename to avoid conflicts
        base_name = Path(cv_path).stem
        timestamp = int(time.time() * 1000) % 100000
        unique_filename = f"{base_name}_test_{timestamp}{Path(cv_path).suffix}"
        
        try:
            with open(cv_path, 'rb') as f:
                content = f.read()
            return content, unique_filename, self.get_content_type(cv_path)
        except Exception as e:
            raise Exception(f"Error reading CV file {cv_path}: {e}")

    # MAIN ENDPOINT TESTS

    @task(2)
    def put_link_existing_candidate_to_job(self):
        """
        PUT /api/v1/job-offers/{job_offer_id}/candidates/{candidate_id}
        Links an existing candidate to a job offer with fit score calculation
        This is the PRIMARY endpoint for testing the main requirement
        """
        job_offer_id = random.choice(self.job_offer_ids)
        candidate_id = random.choice(self.candidate_ids)
        
        with self.client.put(
            f"/api/v1/job-offers/{job_offer_id}/candidates/{candidate_id}",
            catch_response=True,
            name="PUT Link Existing Candidate"
        ) as response:
            if response.status_code in [200, 201, 204]:
                response.success()
            else:
                response.failure(f"PUT failed: {response.status_code} - {response.text}")

    @task(1)
    def post_create_and_link_candidate(self):
        """
        POST /api/v1/job-offers/{job_offer_id}/candidates/
        Creates a new candidate and links it to a job offer
        This tests the alternative workflow
        """
        if not self.test_files["cvs"]:
            return  # Skip if no CV files available
        
        job_offer_id = random.choice(self.job_offer_ids)
        
        try:
            content, filename, content_type = self.get_cv_file_content()
            
            files = {
                'document': (filename, BytesIO(content), content_type)
            }
            
            with self.client.post(
                f"/api/v1/job-offers/{job_offer_id}/candidates/",
                files=files,
                catch_response=True,
                name="POST Create and Link Candidate"
            ) as response:
                if response.status_code == 201:
                    response.success()
                else:
                    response.failure(f"POST failed: {response.status_code} - {response.text}")
                    
        except Exception as e:
            # Use locust's logging instead of print in tasks
            pass

    @task(1)
    def get_job_offer_candidates(self):
        """
        GET /api/v1/job-offers/{job_offer_id}/candidates/
        Retrieves all candidates linked to a specific job offer
        Validates that our PUT/POST operations are working
        """
        job_offer_id = random.choice(self.job_offer_ids)
        
        with self.client.get(
            f"/api/v1/job-offers/{job_offer_id}/candidates/",
            catch_response=True,
            name="GET Job Offer Candidates"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"GET failed: {response.status_code} - {response.text}")

    @task(1)
    def get_all_candidates(self):
        """
        GET /api/v1/candidates/
        Browse all candidates (light monitoring operation)
        """
        params = {
            "skip": random.choice([0, 20, 50]),
            "limit": random.choice([20, 50, 100])
        }
        
        with self.client.get(
            "/api/v1/candidates/",
            params=params,
            catch_response=True,
            name="GET All Candidates"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"GET candidates failed: {response.status_code} - {response.text}")

    @task(1)
    def get_all_job_offers(self):
        """
        GET /api/v1/job-offers/
        Browse all job offers (light monitoring operation)
        """
        params = {
            "skip": random.choice([0, 10, 20]),
            "limit": random.choice([10, 25, 50])
        }
        
        with self.client.get(
            "/api/v1/job-offers/",
            params=params,
            catch_response=True,
            name="GET All Job Offers"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"GET job offers failed: {response.status_code} - {response.text}")

# User types for different testing scenarios

class PutEndpointHeavyUser(MainEndpointTester):
    """User that focuses heavily on PUT endpoint (linking existing candidates)"""
    weight = 3
    
    @task(10)
    def intensive_put_linking(self):
        """Focus on PUT endpoint testing"""
        self.put_link_existing_candidate_to_job()
    
    @task(2)
    def validation_check(self):
        """Check results of linking"""
        self.get_job_offer_candidates()

class PostEndpointHeavyUser(MainEndpointTester):
    """User that focuses on POST endpoint (create and link)"""
    weight = 2
    
    @task(10)
    def intensive_post_creation(self):
        """Focus on POST endpoint testing"""
        self.post_create_and_link_candidate()
    
    @task(3)
    def validation_check(self):
        """Check results of creation"""
        self.get_job_offer_candidates()

class BalancedUser(MainEndpointTester):
    """User that uses both endpoints equally"""
    weight = 4
    
    @task(8)
    def balanced_put(self):
        self.put_link_existing_candidate_to_job()
    
    @task(4)
    def balanced_post(self):
        self.post_create_and_link_candidate()
    
    @task(2)
    def monitor_results(self):
        self.get_job_offer_candidates()

class MonitoringUser(MainEndpointTester):
    """User that primarily monitors data (GET operations)"""
    weight = 1
    wait_time = between(2, 5)  # Slower pace for monitoring
    
    @task(5)
    def monitor_job_candidates(self):
        self.get_job_offer_candidates()
    
    @task(3)
    def monitor_all_candidates(self):
        self.get_all_candidates()
    
    @task(2)
    def monitor_job_offers(self):
        self.get_all_job_offers()

# Event handlers for test lifecycle
@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Called when test starts"""
    print(f"🚀 Focused endpoint testing starting")
    print(f"🎯 Target: {environment.host}")
    print(f"👥 Users: {environment.parsed_options.num_users}")
    print("📊 Primary endpoints:")
    print("   - PUT /api/v1/job-offers/{job_offer_id}/candidates/{candidate_id}")
    print("   - POST /api/v1/job-offers/{job_offer_id}/candidates/")

@events.test_stop.add_listener  
def on_test_stop(environment, **kwargs):
    """Called when test stops"""
    print("🛑 Focused endpoint testing completed")
    print("📈 Check reports for PUT vs POST endpoint performance comparison")
