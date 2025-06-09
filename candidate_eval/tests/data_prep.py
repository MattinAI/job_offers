#!/usr/bin/env python3
"""
Data Preparation Pipeline for CV Analysis Platform
Creates job offers and candidates in the database for load testing
"""

import os
import sys
import json
import time
import requests
from pathlib import Path
from typing import List, Dict, Any
import argparse
from datetime import datetime

class DataPreparationPipeline:
    def __init__(self, api_url: str, output_file: str = "test_data_ids.json"):
        self.api_url = api_url.rstrip('/')
        self.output_file = output_file
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json"})
        
        # Results tracking
        self.created_job_offers = []
        self.created_candidates = []
        self.failed_operations = []
        
    def check_api_health(self) -> bool:
        """Check if API is accessible"""
        print("🔍 Checking API health...")
        
        endpoints_to_try = ["/health", "/api/v1/job-offers/", "/api/v1/candidates/", "/"]
        
        for endpoint in endpoints_to_try:
            try:
                response = self.session.get(f"{self.api_url}{endpoint}", timeout=10)
                if response.status_code < 500:  # Any non-server error is good
                    print(f"✅ API accessible at {self.api_url}{endpoint}")
                    return True
            except requests.RequestException:
                continue
        
        print(f"❌ API not accessible at {self.api_url}")
        return False
    
    def load_test_files(self) -> Dict[str, List[str]]:
        """Load available test files"""
        files = {"cvs": [], "job_descriptions": []}
        
        # Load CV files
        cv_path = Path("test_data/cvs")
        if cv_path.exists():
            for ext in ["*.pdf", "*.docx", "*.txt"]:
                files["cvs"].extend([str(f) for f in cv_path.glob(ext)])
        
        # Load job description files
        job_path = Path("test_data/job_descriptions")
        if job_path.exists():
            for ext in ["*.pdf", "*.docx", "*.txt"]:
                files["job_descriptions"].extend([str(f) for f in job_path.glob(ext)])
        
        return files
    
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
    
    def create_job_offers(self, target_count: int, test_files: Dict[str, List[str]]) -> bool:
        """Create job offers by cycling through available files"""
        if not test_files["job_descriptions"]:
            print("❌ No job description files found!")
            return False
        
        print(f"\n📋 Creating {target_count} job offers...")
        print(f"Using {len(test_files['job_descriptions'])} job description files")
        
        created_count = 0
        file_index = 0
        
        while created_count < target_count:
            job_file = test_files["job_descriptions"][file_index % len(test_files["job_descriptions"])]
            
            # Create unique title
            base_title = Path(job_file).stem.replace('_', ' ').title()
            cycle_number = (file_index // len(test_files["job_descriptions"])) + 1
            title = f"{base_title} - Position #{cycle_number}" if cycle_number > 1 else base_title
            
            try:
                with open(job_file, 'rb') as f:
                    content = f.read()
                
                # Prepare request
                files = {
                    'document': (Path(job_file).name, content, self.get_content_type(job_file))
                }
                data = {'title': title}
                
                # Make request
                response = self.session.post(
                    f"{self.api_url}/api/v1/job-offers/",
                    files=files,
                    data=data,
                    timeout=30
                )
                
                if response.status_code == 201:
                    job_offer = response.json()
                    self.created_job_offers.append({
                        'id': job_offer['id'],
                        'title': title,
                        'source_file': job_file
                    })
                    created_count += 1
                    print(f"  ✅ Created job offer {created_count}: {title} (ID: {job_offer['id']})")
                else:
                    error_msg = f"Failed to create job offer from {job_file}: {response.status_code} - {response.text}"
                    print(f"  ❌ {error_msg}")
                    self.failed_operations.append({
                        'operation': 'create_job_offer',
                        'file': job_file,
                        'error': error_msg
                    })
                
            except Exception as e:
                error_msg = f"Error processing job file {job_file}: {str(e)}"
                print(f"  ❌ {error_msg}")
                self.failed_operations.append({
                    'operation': 'create_job_offer',
                    'file': job_file,
                    'error': error_msg
                })
            
            file_index += 1
            
            # Safety break
            if file_index > target_count * 3:
                print("⚠️ Too many attempts, breaking")
                break
            
            # Small delay to avoid overwhelming the API
            time.sleep(0.1)
        
        print(f"✅ Created {created_count}/{target_count} job offers")
        return created_count > 0
    
    def create_candidates(self, target_count: int, test_files: Dict[str, List[str]]) -> bool:
        """Create candidates by cycling through available CV files"""
        if not test_files["cvs"]:
            print("❌ No CV files found!")
            return False
        
        print(f"\n👥 Creating {target_count} candidates...")
        print(f"Using {len(test_files['cvs'])} CV files")
        
        created_count = 0
        file_index = 0
        
        while created_count < target_count:
            cv_file = test_files["cvs"][file_index % len(test_files["cvs"])]
            
            # Create unique filename
            base_name = Path(cv_file).stem
            cycle_number = (file_index // len(test_files["cvs"])) + 1
            unique_filename = f"{base_name}_candidate_{cycle_number}{Path(cv_file).suffix}"
            
            try:
                with open(cv_file, 'rb') as f:
                    content = f.read()
                
                # Prepare request
                files = {
                    'document': (unique_filename, content, self.get_content_type(cv_file))
                }
                
                # Make request
                response = self.session.post(
                    f"{self.api_url}/api/v1/candidates/",
                    files=files,
                    timeout=30
                )
                
                if response.status_code == 201:
                    candidate = response.json()
                    self.created_candidates.append({
                        'id': candidate['id'],
                        'source_file': cv_file,
                        'unique_filename': unique_filename
                    })
                    created_count += 1
                    
                    # Progress indicator
                    if created_count % 10 == 0:
                        print(f"  📊 Created {created_count} candidates...")
                    elif created_count <= 10:
                        print(f"  ✅ Created candidate {created_count} (ID: {candidate['id']})")
                        
                else:
                    error_msg = f"Failed to create candidate from {cv_file}: {response.status_code} - {response.text}"
                    if created_count <= 5:  # Only show first few errors to avoid spam
                        print(f"  ❌ {error_msg}")
                    self.failed_operations.append({
                        'operation': 'create_candidate',
                        'file': cv_file,
                        'error': error_msg
                    })
                
            except Exception as e:
                error_msg = f"Error processing CV file {cv_file}: {str(e)}"
                if created_count <= 5:
                    print(f"  ❌ {error_msg}")
                self.failed_operations.append({
                    'operation': 'create_candidate',
                    'file': cv_file,
                    'error': error_msg
                })
            
            file_index += 1
            
            # Safety break
            if file_index > target_count * 3:
                print("⚠️ Too many attempts, breaking")
                break
            
            # Small delay to avoid overwhelming the API
            time.sleep(0.05)  # Faster for candidates since they're simpler
        
        print(f"✅ Created {created_count}/{target_count} candidates")
        return created_count > 0
    
    def save_results(self) -> bool:
        """Save created IDs to JSON file for load testing"""
        results = {
            'generated_at': datetime.now().isoformat(),
            'api_url': self.api_url,
            'job_offers': self.created_job_offers,
            'candidates': self.created_candidates,
            'summary': {
                'total_job_offers': len(self.created_job_offers),
                'total_candidates': len(self.created_candidates),
                'failed_operations': len(self.failed_operations)
            },
            'failed_operations': self.failed_operations
        }
        
        try:
            with open(self.output_file, 'w') as f:
                json.dump(results, f, indent=2)
            
            print(f"\n💾 Results saved to: {self.output_file}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to save results: {e}")
            return False
    
    def print_summary(self):
        """Print operation summary"""
        print(f"\n{'='*50}")
        print("📊 DATA PREPARATION SUMMARY")
        print(f"{'='*50}")
        print(f"🎯 API URL: {self.api_url}")
        print(f"📋 Job Offers Created: {len(self.created_job_offers)}")
        print(f"👥 Candidates Created: {len(self.created_candidates)}")
        print(f"❌ Failed Operations: {len(self.failed_operations)}")
        
        if self.created_job_offers:
            print(f"\n📋 Job Offer IDs: {[jo['id'] for jo in self.created_job_offers]}")
        
        if self.created_candidates:
            candidate_ids = [c['id'] for c in self.created_candidates]
            print(f"\n👥 Candidate IDs (first 10): {candidate_ids[:10]}")
            if len(candidate_ids) > 10:
                print(f"    ... and {len(candidate_ids) - 10} more")
        
        if self.failed_operations:
            print(f"\n⚠️ Failed Operations:")
            for failure in self.failed_operations[:5]:  # Show first 5 failures
                print(f"   - {failure['operation']}: {failure['file']} - {failure['error'][:100]}...")
        
        print(f"\n💾 Data saved to: {self.output_file}")
        print("🚀 Ready for load testing!")

def main():
    parser = argparse.ArgumentParser(description="Data Preparation Pipeline for CV Analysis Platform")
    parser.add_argument("--api-url", default="http://localhost:8000", help="API base URL")
    parser.add_argument("--job-offers", type=int, default=10, help="Number of job offers to create")
    parser.add_argument("--candidates", type=int, default=100, help="Number of candidates to create")
    parser.add_argument("--output", default="test_data_ids.json", help="Output file for created IDs")
    parser.add_argument("--check-files", action="store_true", help="Only check available files, don't create data")
    
    args = parser.parse_args()
    
    # Initialize pipeline
    pipeline = DataPreparationPipeline(args.api_url, args.output)
    
    # Load test files
    test_files = pipeline.load_test_files()
    
    print("🏗️ CV Analysis Platform - Data Preparation Pipeline")
    print("=" * 55)
    
    # Check available files
    print(f"📁 Available test files:")
    print(f"   CV files: {len(test_files['cvs'])}")
    print(f"   Job description files: {len(test_files['job_descriptions'])}")
    
    if not test_files["cvs"]:
        print("❌ No CV files found in test_data/cvs/")
        print("Please copy your CV files (.pdf, .docx, .txt) to test_data/cvs/")
        sys.exit(1)
    
    if not test_files["job_descriptions"]:
        print("❌ No job description files found in test_data/job_descriptions/")
        print("Please copy your job description files (.pdf, .docx, .txt) to test_data/job_descriptions/")
        sys.exit(1)
    
    if args.check_files:
        print("✅ File check complete. Files are available for data preparation.")
        return
    
    # Check API health
    if not pipeline.check_api_health():
        sys.exit(1)
    
    print(f"\n🎯 Target: Create {args.job_offers} job offers and {args.candidates} candidates")
    
    # Confirm with user
    response = input("\nProceed with data creation? (y/N): ")
    if response.lower() != 'y':
        print("Operation cancelled.")
        sys.exit(0)
    
    # Create data
    start_time = time.time()
    
    success = True
    success &= pipeline.create_job_offers(args.job_offers, test_files)
    success &= pipeline.create_candidates(args.candidates, test_files)
    
    # Save results
    pipeline.save_results()
    
    # Print summary
    pipeline.print_summary()
    
    elapsed_time = time.time() - start_time
    print(f"\n⏱️ Total time: {elapsed_time:.1f} seconds")
    
    if success and len(pipeline.created_job_offers) > 0 and len(pipeline.created_candidates) > 0:
        print("🎉 Data preparation completed successfully!")
        print("🚀 You can now run the load tests using the generated IDs.")
    else:
        print("⚠️ Data preparation completed with issues. Check the summary above.")
        sys.exit(1)

if __name__ == "__main__":
    main()