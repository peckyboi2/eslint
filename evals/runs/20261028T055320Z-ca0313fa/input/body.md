### Environment

Node version: 24.2.0
npm version: 8.5.5
Local ESLint version: 9.21.0
Global ESLint version: none
Operating System: win32 10.0.19045

### What parser are you using?

@typescript-eslint/parser

### What did you do?

<details>
<summary>Configuration</summary>

```js
import typescriptEslint from "@typescript-eslint/eslint-plugin";
import tsParser from "@typescript-eslint/parser";

export default [
    {
        plugins: {
            "@typescript-eslint": typescriptEslint,
        },
    
        languageOptions: {
            parser: tsParser,
            ecmaVersion: 2023,
            sourceType: "script",
    
            parserOptions: {
                project: "./tsconfig.json",
                projectService: true,
            },
        },

        files: ["App/**/*.ts", "Specs/**/*.ts"],
        ignores: ["**/*.js", "**/*.mjs", "**/*.d.ts"],
    
        rules: {
            semi: "error",
            "@/no-extra-semi": "error",
    
            "@/brace-style": ["error", "1tbs", {
                allowSingleLine: true,
            }],
        
            indent: ["error", 4, {
                SwitchCase: 1,
            }],
    
            "linebreak-style": ["error", "windows"],
            "eol-last": "error",
            "no-case-declarations": "error",
            "no-trailing-spaces": "error",
            "no-sequences": "error",
            "@typescript-eslint/unbound-method": ["error", {}],
        },
    },
    {
        files: ["Specs/**/*.ts"],
        ignores: ["**/*.js", "**/*.mjs", "**/*.d.ts"],
    
        rules: {
            "@typescript-eslint/unbound-method": "off",
        },
     }
];
```

Triggering code in build\test.js: 
```      // eslint-disable-next-line react-internal/no-production-logging``` 

In short, we are using Gulp to lint our Typescript in parallel with building it. We explicitly specify the desired linted files, but eslint keeps linting other files as well, even though we explicitly ignore them.

### What did you expect to happen?

The linter should pass because the actual Typescript we're actually linting doesn't have any failures.

### What actually happened?

The linter fails.

Error:
```C:\dev\eslint-file-included\build\test.js(1,1): error react-internal/no-producton-logging : Definition for rule 'react-internal/no-production-logging' was not found.```

### Link to Minimal Reproducible Example

https://github.com/markboyall/eslint-file-included

### Participation

- [ ] I am willing to submit a pull request for this issue.

### Additional comments

_No response_