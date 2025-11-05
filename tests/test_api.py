import httpx
import pytest
import time
import os

BASE_URL = "http://localhost:8000/api/v1"
shared_data = {}


@pytest.mark.order(1)
def test_01_health_check():
    """
    Test 1: Check if the API and DB are healthy before doing anything else.
    """
    print("\n--- Test 1: Health Check ---")
    try:
        response = httpx.get(f"{BASE_URL}/health")
        response.raise_for_status()  
        
        data = response.json()
        print(f"Health check response: {data}")
        
        assert response.status_code == 200
        assert data["api_status"] == "ok"
        assert data["db_status"] == "ok"
        
    except httpx.ConnectError as e:
        pytest.fail(f"Could not connect to API. Is it running? {e}", pytrace=False)
    except Exception as e:
        pytest.fail(f"Health check failed: {e}", pytrace=False)

@pytest.mark.order(2)
def test_02_upload_resume():
    """
    Test 2: Upload the 'test_resume.txt' file and get a new ID.
    """
    print("\n--- Test 2: Upload Resume ---")
    
    file_path = "tests/test_resume.txt"
    
    if not os.path.exists(file_path):
        pytest.fail(f"Test file not found at {file_path}. Make sure it exists.", pytrace=False)
        
    with open(file_path, "rb") as f:
        files = {"file": (os.path.basename(file_path), f, "text/plain")}
        
        try:
            response = httpx.post(f"{BASE_URL}/resumes/upload", files=files, timeout=30.0)
            response.raise_for_status()
            
            data = response.json()
            print(f"Upload response: {data}")
            
            assert response.status_code == 200
            assert "id" in data
            assert data["status"] == "processing"
            assert data["file_name"] == "test_resume.txt"
            
            shared_data["resume_id"] = data["id"]
            
        except Exception as e:
            pytest.fail(f"Upload failed: {e}", pytrace=False)

@pytest.mark.order(3)
def test_03_poll_for_completion():
    """
    Test 3: Poll the /status endpoint until the resume is 'completed'.
    This is a long-running test.
    """
    if "resume_id" not in shared_data:
        pytest.skip("No resume_id found, skipping status poll.")
        
    resume_id = shared_data["resume_id"]
    print(f"\n--- Test 3: Polling for Status (ID: {resume_id}) ---")
    
    timeout = 120  # 2 minutes total timeout (generous for multiple AI calls)
    poll_interval = 5  # 5 seconds
    start_time = time.time()
    
    while True:
        try:
            current_time = time.time()
            if current_time - start_time > timeout:
                pytest.fail(f"Timeout: Resume processing took longer than {timeout} seconds.", pytrace=False)
            
            response = httpx.get(f"{BASE_URL}/resumes/{resume_id}/status")
            response.raise_for_status()
            
            data = response.json()
            print(f"Current status: {data['status']}")
            
            if data["status"] == "completed":
                assert True
                break  # Success!
            elif data["status"] in ["parse_failed", "ai_failed"]:
                pytest.fail(f"Resume processing failed with status: {data['status']}", pytrace=False)
            
            # Wait before polling again
            time.sleep(poll_interval)
            
        except Exception as e:
            pytest.fail(f"Status check failed: {e}", pytrace=False)

@pytest.mark.order(4)
def test_04_get_resume_data():
    """
    Test 4: Retrieve the full, parsed data and verify 'ground truth'.
    """
    if "resume_id" not in shared_data:
        pytest.skip("No resume_id found, skipping data retrieval.")
        
    resume_id = shared_data["resume_id"]
    print(f"\n--- Test 4: Get Resume Data (ID: {resume_id}) ---")
    
    try:
        response = httpx.get(f"{BASE_URL}/resumes/{resume_id}")
        response.raise_for_status()
        
        data = response.json()
        
        assert response.status_code == 200
        assert data["id"] == resume_id
        
        # Verify metadata
        assert data["metadata"]["file_name"] == "test_resume.txt"
        
        # Verify ground truth from the parser
        assert data["personalInfo"]["name"]["full"] == "John Doe"
        assert data["personalInfo"]["contact"]["email"] == "john.doe@email.com"
        assert "Senior Software Engineer" in data["experience"][0]["title"]
        assert "Python" in data["skills"]["technical"][0]["items"]
        assert "AWS Certified Solutions Architect - Associate" in data["certifications"][0]["name"]
        
        # Verify AI enhancements
        assert data["aiEnhancements"]["qualityScore"] > 70
        assert data["aiEnhancements"]["biasReport"]["biasDetected"] is True
        
        print("Data verification successful.")
        
    except Exception as e:
        pytest.fail(f"GET /resumes/{id} failed: {e}", pytrace=False)

@pytest.mark.order(5)
def test_05_match_resume():
    """
    Test 5: Test the /match endpoint with the completed resume.
    """
    if "resume_id" not in shared_data:
        pytest.skip("No resume_id found, skipping match test.")
        
    resume_id = shared_data["resume_id"]
    print(f"\n--- Test 5: Match Resume (ID: {resume_id}) ---")
    
    # A simple job description to test against
    job_description = {
        "jobDescription": {
            "title": "Senior Python Developer",
            "skills": {
                "required": ["Python", "AWS", "PostgreSQL"],
                "preferred": ["FastAPI", "Kubernetes"]
            }
        }
    }
    
    try:
        response = httpx.post(f"{BASE_URL}/resumes/{resume_id}/match", json=job_description, timeout=60.0)
        response.raise_for_status()
        
        data = response.json()
        
        assert response.status_code == 200
        assert data["resumeId"] == resume_id
        assert data["jobTitle"] == "Senior Python Developer"
        assert data["matchingResults"]["overallScore"] > 70  # Should be a strong match
        assert data["matchingResults"]["categoryScores"]["skillsMatch"]["score"] > 80
        
        print(f"Match successful. Overall Score: {data['matchingResults']['overallScore']}")
        
    except Exception as e:
        pytest.fail(f"POST /match failed: {e}", pytrace=False)

@pytest.mark.order(6)
def test_06_get_analytics():
    """
    Test 6: Test the /analytics endpoint.
    """
    if "resume_id" not in shared_data:
        pytest.skip("No resume_id found, skipping analytics test.")
        
    resume_id = shared_data["resume_id"]
    print(f"\n--- Test 6: Get Analytics (ID: {resume_id}) ---")
    
    try:
        response = httpx.get(f"{BASE_URL}/analytics/resume/{resume_id}")
        response.raise_for_status()
        
        data = response.json()
        
        assert response.status_code == 200
        assert data["id"] == resume_id
        assert data["status"] == "completed"
        assert data["ai_enhancements"]["qualityScore"] > 70
        assert "salaryEstimate" in data["ai_enhancements"]
        
        print("Analytics retrieval successful.")
        
    except Exception as e:
        pytest.fail(f"GET /analytics failed: {e}", pytrace=False)

@pytest.mark.order(7)
def test_07_delete_resume():
    """
    Test 7: Delete the resume we created.
    """
    if "resume_id" not in shared_data:
        pytest.skip("No resume_id found, skipping delete test.")
        
    resume_id = shared_data["resume_id"]
    print(f"\n--- Test 7: Delete Resume (ID: {resume_id}) ---")
    
    try:
        response = httpx.delete(f"{BASE_URL}/resumes/{resume_id}")
        response.raise_for_status()
        
        data = response.json()
        
        assert response.status_code == 200
        assert data["message"] == "Resume deleted successfully"
        
        print("Delete successful.")
        
    except Exception as e:
        pytest.fail(f"DELETE /resumes/{id} failed: {e}", pytrace=False)

@pytest.mark.order(8)
def test_08_verify_delete():
    """
    Test 8: Verify that the resume is truly gone (should 404).
    """
    if "resume_id" not in shared_data:
        pytest.skip("No resume_id found, skipping delete verification.")
        
    resume_id = shared_data["resume_id"]
    print(f"\n--- Test 8: Verify Delete (ID: {resume_id}) ---")
    
    try:
        with httpx.Client() as client:
            response = client.get(f"{BASE_URL}/resumes/{resume_id}/status")
            
            assert response.status_code == 404
            assert "Resume not found" in response.json()["detail"]
            
            print("Delete verified (404 Not Found).")
            
    except Exception as e:
        pytest.fail(f"Delete verification failed: {e}", pytrace=False)