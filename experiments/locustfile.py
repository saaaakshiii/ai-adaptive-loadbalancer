from locust import HttpUser, task, between

class LoadBalancerUser(HttpUser):
    wait_time = between(0.01, 0.1)

    @task
    def request_work(self):
        self.client.get("/proxy/work?delay=0.05", name="/proxy/work")
