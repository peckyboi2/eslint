### Environment

Node version: v24.12.0
npm version: 11.6.2
Local ESLint version: v10.0.3
Global ESLint version: Not installed
Operating System: Windows 11 (10.0.26200) x64

### What parser are you using?

Default (Espree)

### What did you do?

`@eslint/plugin-kit@0.6.1` publishes raw TypeScript source files (`types.ts`) in `dist/esm/` alongside the compiled `types.d.ts` declaration file. The published tarball contains:

```
package/dist/esm/types.ts    ← raw TS source (should not be published)
package/dist/esm/types.d.ts  ← correct declaration file
package/dist/esm/index.js
package/dist/esm/index.d.ts
package/dist/cjs/types.cts   ← also raw source (no types.cjs counterpart)
```

When a bundler (webpack) has `.ts` in its `resolve.extensions` list and `index.d.ts` imports `./types` (without extension), the bundler resolves `./types` to `types.ts` instead of `types.d.ts` because `.ts` takes priority. This causes build tools like Angular's `@ngtools/webpack` to include the file in the TypeScript compilation program, then warn that it's unused.

<details>
<summary>Configuration</summary>

```js
// webpack.config.js (Angular renderer)
module.exports = {
  resolve: {
    extensions: ['.ts', '.tsx', '.js', '.mjs', '.css', '.json']
  },
  plugins: [
    new AngularWebpackPlugin({
      tsconfig: './tsconfig.angular.json'
    })
  ]
};
```

</details>

```js
// No user code needed to reproduce — the warning fires from the published
// package structure alone when .ts is in webpack's resolve.extensions
```

### What did you expect to happen?

The Angular compiler (via `@ngtools/webpack`) picks up `types.ts` through TypeScript's module resolution when processing type imports within `@eslint/plugin-kit`. Since `types.ts` is a source file that no application code imports directly, Angular flags it as "part of the TypeScript compilation but unused":

```
WARNING
C:/path/to/node_modules/@eslint/plugin-kit/dist/esm/types.ts is part of the TypeScript compilation but it's unused.
Add only entry points to the 'files' or 'include' properties in your tsconfig.
```

This affects any project using webpack with `.ts` in `resolve.extensions` (standard for Angular, React with TypeScript, etc.) where `@eslint/plugin-kit` is installed as a transitive dependency of ESLint 10.

**Expected:** Published packages should only contain compiled `.js` and `.d.ts` files — not raw `.ts` source. The `types.ts` and `types.cts` files should be excluded from the published tarball.

**Suggested fix:** Add `"!**/*.ts"` and `"!**/*.cts"` exclusions to the `files` field in `package.json`, or adjust the build pipeline to not emit source `.ts` files into `dist/`.


### What actually happened?

Workaround for others hitting this: add a postinstall script to delete the file:

{
  "scripts": {
    "postinstall": "node -e \"require('fs').rmSync('node_modules/@eslint/plugin-kit/dist/esm/types.ts',{force:true})\""
  }
}

### Link to Minimal Reproducible Example

https://eslint.org/play/#eyJ0ZXh0IjoiLyogU2VlIGlzc3VlIGRlc2NyaXB0aW9uIOKAlCB0aGlzIGlzIGEgcGFja2FnaW5nIGJ1Zywgbm90IGEgbGludGluZyBpc3N1ZS4gKi9cbiIsIm9wdGlvbnMiOnsicnVsZXMiOnsiY29uc3RydWN0b3Itc3VwZXIiOlsiZXJyb3IiXSwiZm9yLWRpcmVjdGlvbiI6WyJlcnJvciJdLCJnZXR0ZXItcmV0dXJuIjpbImVycm9yIl0sIm5vLWFzeW5jLXByb21pc2UtZXhlY3V0b3IiOlsiZXJyb3IiXSwibm8tY2FzZS1kZWNsYXJhdGlvbnMiOlsiZXJyb3IiXSwibm8tY2xhc3MtYXNzaWduIjpbImVycm9yIl0sIm5vLWNvbXBhcmUtbmVnLXplcm8iOlsiZXJyb3IiXSwibm8tY29uZC1hc3NpZ24iOlsiZXJyb3IiXSwibm8tY29uc3QtYXNzaWduIjpbImVycm9yIl0sIm5vLWNvbnN0YW50LWJpbmFyeS1leHByZXNzaW9uIjpbImVycm9yIl0sIm5vLWNvbnN0YW50LWNvbmRpdGlvbiI6WyJlcnJvciJdLCJuby1jb250cm9sLXJlZ2V4IjpbImVycm9yIl0sIm5vLWRlYnVnZ2VyIjpbImVycm9yIl0sIm5vLWRlbGV0ZS12YXIiOlsiZXJyb3IiXSwibm8tZHVwZS1hcmdzIjpbImVycm9yIl0sIm5vLWR1cGUtY2xhc3MtbWVtYmVycyI6WyJlcnJvciJdLCJuby1kdXBlLWVsc2UtaWYiOlsiZXJyb3IiXSwibm8tZHVwZS1rZXlzIjpbImVycm9yIl0sIm5vLWR1cGxpY2F0ZS1jYXNlIjpbImVycm9yIl0sIm5vLWVtcHR5IjpbImVycm9yIl0sIm5vLWVtcHR5LWNoYXJhY3Rlci1jbGFzcyI6WyJlcnJvciJdLCJuby1lbXB0eS1wYXR0ZXJuIjpbImVycm9yIl0sIm5vLWVtcHR5LXN0YXRpYy1ibG9jayI6WyJlcnJvciJdLCJuby1leC1hc3NpZ24iOlsiZXJyb3IiXSwibm8tZXh0cmEtYm9vbGVhbi1jYXN0IjpbImVycm9yIl0sIm5vLWZhbGx0aHJvdWdoIjpbImVycm9yIl0sIm5vLWZ1bmMtYXNzaWduIjpbImVycm9yIl0sIm5vLWdsb2JhbC1hc3NpZ24iOlsiZXJyb3IiXSwibm8taW1wb3J0LWFzc2lnbiI6WyJlcnJvciJdLCJuby1pbnZhbGlkLXJlZ2V4cCI6WyJlcnJvciJdLCJuby1pcnJlZ3VsYXItd2hpdGVzcGFjZSI6WyJlcnJvciJdLCJuby1sb3NzLW9mLXByZWNpc2lvbiI6WyJlcnJvciJdLCJuby1taXNsZWFkaW5nLWNoYXJhY3Rlci1jbGFzcyI6WyJlcnJvciJdLCJuby1uZXctbmF0aXZlLW5vbmNvbnN0cnVjdG9yIjpbImVycm9yIl0sIm5vLW5vbm9jdGFsLWRlY2ltYWwtZXNjYXBlIjpbImVycm9yIl0sIm5vLW9iai1jYWxscyI6WyJlcnJvciJdLCJuby1vY3RhbCI6WyJlcnJvciJdLCJuby1wcm90b3R5cGUtYnVpbHRpbnMiOlsiZXJyb3IiXSwibm8tcmVkZWNsYXJlIjpbImVycm9yIl0sIm5vLXJlZ2V4LXNwYWNlcyI6WyJlcnJvciJdLCJuby1zZWxmLWFzc2lnbiI6WyJlcnJvciJdLCJuby1zZXR0ZXItcmV0dXJuIjpbImVycm9yIl0sIm5vLXNoYWRvdy1yZXN0cmljdGVkLW5hbWVzIjpbImVycm9yIl0sIm5vLXNwYXJzZS1hcnJheXMiOlsiZXJyb3IiXSwibm8tdGhpcy1iZWZvcmUtc3VwZXIiOlsiZXJyb3IiXSwibm8tdW5hc3NpZ25lZC12YXJzIjpbImVycm9yIl0sIm5vLXVuZGVmIjpbImVycm9yIl0sIm5vLXVuZXhwZWN0ZWQtbXVsdGlsaW5lIjpbImVycm9yIl0sIm5vLXVucmVhY2hhYmxlIjpbImVycm9yIl0sIm5vLXVuc2FmZS1maW5hbGx5IjpbImVycm9yIl0sIm5vLXVuc2FmZS1uZWdhdGlvbiI6WyJlcnJvciJdLCJuby11bnNhZmUtb3B0aW9uYWwtY2hhaW5pbmciOlsiZXJyb3IiXSwibm8tdW51c2VkLWxhYmVscyI6WyJlcnJvciJdLCJuby11bnVzZWQtcHJpdmF0ZS1jbGFzcy1tZW1iZXJzIjpbImVycm9yIl0sIm5vLXVudXNlZC12YXJzIjpbImVycm9yIl0sIm5vLXVzZWxlc3MtYXNzaWdubWVudCI6WyJlcnJvciJdLCJuby11c2VsZXNzLWJhY2tyZWZlcmVuY2UiOlsiZXJyb3IiXSwibm8tdXNlbGVzcy1jYXRjaCI6WyJlcnJvciJdLCJuby11c2VsZXNzLWVzY2FwZSI6WyJlcnJvciJdLCJuby13aXRoIjpbImVycm9yIl0sInByZXNlcnZlLWNhdWdodC1lcnJvciI6WyJlcnJvciJdLCJyZXF1aXJlLXlpZWxkIjpbImVycm9yIl0sInVzZS1pc25hbiI6WyJlcnJvciJdLCJ2YWxpZC10eXBlb2YiOlsiZXJyb3IiXX0sImxhbmd1YWdlT3B0aW9ucyI6eyJwYXJzZXJPcHRpb25zIjp7ImVjbWFGZWF0dXJlcyI6e319fX19

### Participation

- [x] I am willing to submit a pull request for this issue.

### AI acknowledgment

- [ ] I did not use AI to generate this issue report.
- [x] (If the above is not checked) I have reviewed the AI-generated content before submitting.

### Additional comments

Workaround for others hitting this: add a `postinstall` script to delete the file:

```json
{
  "scripts": {
    "postinstall": "node -e \"require('fs').rmSync('node_modules/@eslint/plugin-kit/dist/esm/types.ts',{force:true})\""
  }
}
```