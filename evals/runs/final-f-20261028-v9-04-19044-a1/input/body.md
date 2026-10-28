### Environment

Local ESLint version: 9.13.0

### What parser are you using?

Default (Espree)

### What did you do?

No `"type"` declared inside `package.json`.

Three _blank_ config files:

- `eslint.config.cjs`
- `eslint.config.js`
- `eslint.config.mjs`

### What did you expect to happen?

ESLint should give the same output no matter which of the three blank config files are used.

### What actually happened?

- `npx eslint -c eslint.config.cjs`: no output
- `npx eslint -c eslint.config.js`: no output
- `npx eslint -c eslint.config.mjs`: the following error message was displayed:
```
Oops! Something went wrong! :(

ESLint: 9.13.0

TypeError: Config (unnamed): Unexpected undefined config at user-defined index 0.
```

### Link to Minimal Reproducible Example

https://github.com/abrahamguo/repro/tree/eslint-no-export

### Participation

- [x] I am willing to submit a pull request for this issue.

### Additional comments

_No response_