run

```bash
npx eslint -c .eslintrc.yml ../tmp/outer_example.js
```

result:

```
  1:1   warning  Unexpected console statement                                     no-console
  1:13  error    Strings must use singlequote                                     quotes
  1:22  error    Missing semicolon                                                semi
  2:1   error    All 'var' declarations must be at the top of the function scope  vars-on-top
  2:1   error    Unexpected var, use let or const instead                         no-var
  2:5   error    'y' is assigned a value but never used                           no-unused-vars
  2:12  error    Missing semicolon
```
