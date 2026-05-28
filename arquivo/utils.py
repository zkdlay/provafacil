import base64


class Utils:

    @staticmethod
    def file_to_base64(file):

        if not file:
            return None

        return base64.b64encode(
            file.read()
        ).decode("utf-8")