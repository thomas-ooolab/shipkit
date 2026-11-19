# Answer with evidence you fetched this turn

Applies to every answer or report a skill gives a person: a Slack reply, a Jira comment, a report to the user in the terminal.

**The rule.** Every claim about code, configuration, server state or system behavior has evidence taken in this turn: a file you read, a
read-only command you ran, a call you made. A fact the answer needs that a read-only action within the access you already hold can check
(read the file or the function, grep, print a config value, a read-only `ssh` to a host the skill may reach, a `GET` against a non-production
API) is checked **first**, and the answer states what it showed. The access you hold is bounded by the skill's own scope (`/verify` and `/developer`
never touch production), so a check outside it is not available — see below.

**"Not verified" is for what cannot be checked**, and only in this shape: *what* blocks it (no access to X, someone else has to do Y, the check
would change something), *who or what opens it* (which person, which credential, which command with the user's go-ahead), and *what you
already tried*. "Not checked", "haven't read it", "can't say for sure" on a fact you could have read is not an answer: the person asks again, the
check takes one command, and it comes back with the result.

**A guess is not a finding.** What you did not check is written as a question or an open item, never as a conclusion ("probably", "should be",
"standard behavior" included).

**A name search is not a dependency check.** A `grep` proves only that a name is absent from the text. To claim "nothing depends on X", "no test relies on
X" or "this is not affected", read how the consumers get their data: a mock that returns the same pointer twice, a fixture, a shared slice or map, a
constructor that copies or does not. When it is cheap, make the change in a scratch copy and run the tests of that package. *Example (AR-684):* a reviewer said
a committed test reuses the run pointer; the coordinator left the advisory without reading the test, then told the user the reason was unverified because
`grep DeliveredKeys` in the tests found nothing. Reading `worker_redelivery_test.go` showed the reviewer was right: the `GetByID` mock returns the same `*ReportRun`
twice and `Deliver` appends to it in place, so the test depends on a field it never names. A reviewer's note is a lead to read, not a reason; a grep that
finds nothing is not "no".

**A correction is a claim too.** Before telling a person "my earlier reason was wrong", or "your reason was wrong", check the correction the same way as the original
claim, in both directions: what would show the first claim right, and what would show it wrong. A flip-flop costs more trust than a plain "not checked yet".

| Excuse | Reality |
|---|---|
| "I'll say it's unchecked, they can ask me to look" | They will, and the check was one read. Do it now, answer with the result. |
| "It's long / I'd have to open the config" | Opening it is the job. A long file is a grep. |
| "It's probably the same as staging" | Prod you cannot reach is a named blocker (no credentials; who has them), not a guess about its value. |
| "I read the code, so the server does that" | Code says what should run, the host says what runs. If a read-only look at the host is allowed, take it. |
| "A caveat at the end covers me" | A caveat on a checkable fact is the failure this file is about. |
| "A grep for the name found nothing, so nothing depends on it" | A grep proves only that the name is absent. Read how the consumers build their data, or run the change in a scratch copy. |
| "The earlier reason was wrong, I'll say so" | Check the correction as the original: in both directions, before it reaches the person. |
