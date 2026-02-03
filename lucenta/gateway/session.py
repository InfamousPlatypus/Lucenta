import time

class SessionManager:
    def __init__(self, lease_duration=1800): # 30 minutes
        self.lease_duration = lease_duration
        self.leases = {} # user_id -> expiry_time

    def grant_lease(self, user_id: str):
        self.leases[user_id] = time.time() + self.lease_duration
        print(f"Lease granted for {user_id} until {self.leases[user_id]}")

    def is_authorized(self, user_id: str) -> bool:
        expiry = self.leases.get(user_id, 0)
        authorized = time.time() < expiry
        if not authorized:
            print(f"User {user_id} is not authorized.")
        return authorized
