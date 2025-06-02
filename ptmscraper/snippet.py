from io import BytesIO
from PyPDF2 import PdfReader


def extract_snippet(resp, context=150):
    """Extract text snippet around 'Heartland Payroll' from PDF response.

    Parameters
    ----------
    resp : object
        Any object with a ``content`` attribute containing PDF bytes.
    context : int
        Number of characters of context to include around the keyword.

    Returns
    -------
    str
        The extracted snippet or an empty string if the keyword is not found.
    """
    reader = PdfReader(BytesIO(resp.content))
    text = "".join(page.extract_text() or "" for page in reader.pages)

    pos = text.lower().find("heartland payroll")
    if pos == -1:
        return ""

    keyword = "heartland payroll"
    start = max(pos - context, 0)
    end = pos + len(keyword) + context
    return text[start:end]
