from abc import ABC, abstractmethod


class AbstractEmailService(ABC):
    @abstractmethod
    def send_activation_code(self, recipient_email: str, code: str) -> bool:
        raise NotImplementedError
