### Environment

ESLint 10.10.0 and main commit 45ad79e54a39b54b4ce8eb47e612bd2f72a7a651; Node 22.23.2; Ubuntu.

### Parser

Default (Espree).

### What did you do?

```js
const { Linter } = require("eslint");
const code = "const obj = { describe() { return super.toString(); } }; obj.describe();";
const result = new Linter().verifyAndFix(code, {
  languageOptions: { ecmaVersion: 2022, sourceType: "script" },
  rules: { "object-shorthand": ["error", "never"] }
});
console.log(result);
```

### What did you expect?

Preserve valid syntax and behavior, or leave the diagnostic without an unsafe automatic fix.

### What actually happened?

`verifyAndFix()` returns `fixed: true` with this output and a fatal `Parsing error: 'super' keyword outside a method` diagnostic:

```js
const obj = { describe: function() { return super.toString(); } }; obj.describe();
```

The input evaluates to `[object Object]`; the output fails to parse. A method using `this.toString()` instead remains valid after fixing. CLI file writes were not tested.

### Link to Minimal Reproducible Example

[ESLint Playground](https://eslint.org/play#eyJ0ZXh0IjoiY29uc3Qgb2JqID0geyBkZXNjcmliZSgpIHsgcmV0dXJuIHN1cGVyLnRvU3RyaW5nKCk7IH0gfTsgb2JqLmRlc2NyaWJlKCk7Iiwib3B0aW9ucyI6eyJydWxlcyI6eyJvYmplY3Qtc2hvcnRoYW5kIjpbImVycm9yIiwibmV2ZXIiXX0sImxhbmd1YWdlT3B0aW9ucyI6eyJlY21hVmVyc2lvbiI6MjAyMiwic291cmNlVHlwZSI6InNjcmlwdCJ9fX0=)

### AI acknowledgment

GPT-6 Astra assisted; I manually reviewed this report.
