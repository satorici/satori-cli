# Asserts


You can assert several things:

| Assert                  | Value          | Description                             |
|-------------------------|----------------|-----------------------------------------|
| assertStdout            | Boolean        | Is output produced?
| assertStdoutEquals      | String\*       | Is the output equal to the String?
| assertStdoutNotEquals   | String         | Is the output different than String?
| assertStdoutContains    | String         | Does the output contains the String?
| assertStdoutNotContains | String         | Does the output not contain the String?
| assertStdoutSHA256      | SHA256Checksum | Is the output equal to this SHA256 hash?
| assertStdoutRegex       | Regex          | Does the output matches your regexp?
| assertStdoutNotRegex    | Regex          | Does the output not match your regexp?
| assertStderr            | Boolean        | Are errors produced?
| assertStderrEquals      | String\*       | Is the error equal to the String?
| assertStderrNotEquals   | String         | Is the error different than String?
| assertStderrContains    | String         | Does the error contains the String?
| assertStderrNotContains | String         | Does the error not contain the String?
| assertStderrSHA256      | SHA256Checksum | Is the error equal to this SHA256 hash?
| assertStderrRegex       | Regex          | Does the error matches your regexp?
| assertStderrNotRegex    | Regex          | Does the error not match your regexp?
| assertReturnCode        | Integer        | Is the return code equal to the Integer?
| assertSoftwareExists    | Boolean        | Does the software being executed exists? True by default
| assertDifferent         | Boolean        | Does the execution behaves differently when using different inputs?
| assertKilled            | Boolean        | Did the software timed out?

Please let us know if you need asserts not currently covered.
