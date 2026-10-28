run

```bash
  npx eslint -c eslint.config.mjs ../tmp/outer_example.js
```

result (bug!):


```
  0:0  warning  File ignored because outside of base path
```
