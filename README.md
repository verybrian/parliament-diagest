#### Overview

A tool that fetches the latest bill from the Kenyan National Assembly published on the Parliament website, generates a summary using Gemini AI, and sends it to my email on a daily basis.

I wanted a way to keep up with the bills proposed without navigating the website manually every day and reading through legal jargon to make sense of each bill.

#### How it works

The scraper runs every day at 5:00 PM EAT via GitHub Actions. It fetches the first page of the [National Assembly Bills listing](https://parliament.go.ke/the-national-assembly/house-business/bills) and compares it against a local record of already-processed bills. Only new bills are processed.

For each new bill, the scraper:

1. Downloads the gazette PDF
2. Skips the cover and blank pages, then OCRs pages 3–10 for the bill content
3. Also scans the last 4 pages separately to locate the endorser and endorsement date, since these always appear near the end of the document
4. Sends the extracted text to Google Gemini 2.5 Flash for summarization
5. Emails the summary to everyone in `recipients.txt`

Each digest email contains:

- **Bill title**
- **Gazette date** — when the bill was published in the Kenya Gazette
- **Endorsement date** — when the bill was signed and submitted _(where available)_
- **Endorsed by** — the MP or any other sponsor _(where available)_
- **The problem** — what situation or gap the bill is responding to
- **The proposal** — what the bill intends to do about it
- **Who is affected** — citizens, businesses, county governments, etc.
- **Key changes** — 3–6 plain-English bullet points on the specific amendments
- **A link** to the full gazette PDF

Some fields such as the endorser and endorsement date may not be present in all bills. In those cases the field is marked as _Not specified_ in the email.

#### Example

![Example of a bill summary](/media/example_email.png)<br>
_Example of a bill summary_

---

#### Subscribe

You can add yourself to the mailing list by opening a PR with your email address to `recipients.txt`. Your email will be publicly visible in the repository, so consider using a throwaway address or an alias from a service like [DuckDuckGo Email Protection](https://duckduckgo.com/email/) or [SimpleLogin](https://simplelogin.io/).

To unsubscribe, open a PR removing your address from `recipients.txt`.

---

#### Stack

| Component          | Tool                          | Cost      |
| ------------------ | ----------------------------- | --------- |
| Scheduler & runner | GitHub Actions                | Free      |
| Scraping           | `requests` + `BeautifulSoup4` | Free      |
| PDF extraction     | `pdf2image` + `pytesseract`   | Free      |
| AI summarization   | Google Gemini 2.5 Flash       | Free tier |
| Email delivery     | Gmail SMTP                    | Free      |
