from src.services.email_interfaces import AbstractEmailService

class MockEmailService(AbstractEmailService):
    def send_activation_code(self, recipient_email: str, code: str) -> bool:
        print(f"Mock sending activation code to {recipient_email} with code '{code}'")
        return True