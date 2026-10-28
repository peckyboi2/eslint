### Environment

Node version: 22.11.0
npm version: 10.9.0
Local ESLint version: 9.28.0
Global ESLint version: 9.28.0
Operating System: Windows


### What parser are you using?

Default (Espree)

### What did you do?

eslint ./ --fix

### What did you expect to happen?

All files with auto-fixable issues are fixed.

### What actually happened?

Running `--fix` command in a big repository with 106152 problems and 103.985 auto-fixable issues across ~9000 files. 
I constantly get EMFILE: too many open files error:
`at async open (node:internal/fs/promises:638:25)
    at async Object.writeFile (node:internal/fs/promises:1208:14)
    at async Promise.all (index 8189)
    at async ESLint.outputFixes (...\node_modules\eslint\lib\eslint\eslint.js:534:3)
    at async Object.execute (...\node_modules\eslint\lib\cli.js:642:4)
    at async main (...\node_modules\eslint\bin\eslint.js:175:19)`
https://github.com/eslint/eslint/blob/main/lib/eslint/eslint.js#L533 this happens here!

### Link to Minimal Reproducible Example

/

### Participation

- [ ] I am willing to submit a pull request for this issue.

### Additional comments

Is there a workaround I can set that will work on windows and linux. 
As a QA engineer, I am providing a list of rules and configurations for ESLint for different implementation teams within our company.  Which means all rules will be applied from 0 only once.