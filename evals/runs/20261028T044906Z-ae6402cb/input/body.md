### Environment

Node version: 23.11.0
npm version: 11.3.0
Local ESLint version: 9.28.0
Global ESLint version:
Operating System: Ubuntu 24.04


### What parser are you using?

Default (Espree)

### What did you do?

Unexpected error with increment/decrement

```js
/* eslint no-useless-assignment: "error" */

// shows error
[1, 2, 3].map(i => i++);
[1, 2, 3].map(i => i--);

// no error
[1, 2, 3].map(i => i + 1);
[1, 2, 3].map(i => i - 1);
```

### What did you expect to happen?

No error

### What actually happened?

> This assigned value is not used in subsequent statements.  ([no-useless-assignment](https://eslint.org/docs/rules/no-useless-assignment))

### Link to Minimal Reproducible Example

https://eslint.org/play/#eyJ0ZXh0IjoiLyogZXNsaW50IG5vLXVzZWxlc3MtYXNzaWdubWVudDogXCJlcnJvclwiICovXG5cbi8vIHNob3dzIGVycm9yXG5bMSwgMiwgM10ubWFwKGkgPT4gaSsrKTtcblsxLCAyLCAzXS5tYXAoaSA9PiBpLS0pO1xuXG4vLyBubyBlcnJvclxuWzEsIDIsIDNdLm1hcChpID0+IGkgKyAxKTtcblsxLCAyLCAzXS5tYXAoaSA9PiBpIC0gMSk7Iiwib3B0aW9ucyI6eyJydWxlcyI6eyJuby11c2VsZXNzLWFzc2lnbm1lbnQiOlsiZXJyb3IiXX0sImxhbmd1YWdlT3B0aW9ucyI6eyJwYXJzZXJPcHRpb25zIjp7ImVjbWFGZWF0dXJlcyI6e319fX19

### Participation

- [ ] I am willing to submit a pull request for this issue.

### Additional comments


