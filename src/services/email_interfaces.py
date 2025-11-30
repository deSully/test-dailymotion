from abc import ABC, abstractmethod

class AbstractEmailService(ABC):
    @abstractmethod
    def send_email(self, to_address: str, subject: str, body: str) -> bool:
        raise NotImplementedError