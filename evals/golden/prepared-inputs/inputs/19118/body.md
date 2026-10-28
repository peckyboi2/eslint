### Environment

eslint version: v9.14.0

### What parser are you using?

Default (Espree)

### What did you do?

I have config file inside: /app/eslint.config.mjs and want to lint files inside /tmp/example.js

root@container:/app  npx eslint --flag unstable_config_lookup_from_file -c "./eslint.config.mjs" /tmp/example.js

```
/tmp/example.js
  0:0  warning  File ignored because outside of base path
```

### What did you expect to happen?

behaviour as before version 9.0, should check the file

### What actually happened?

 File ignored because outside of base path

### Link to Minimal Reproducible Example

https://github.com/Peredery/eslint_bug_report_-File-ignored-because-outside-of-base-path

### Participation

- [ ] I am willing to submit a pull request for this issue.

### Additional comments

_No response_