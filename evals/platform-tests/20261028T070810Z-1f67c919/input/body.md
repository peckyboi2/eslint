### Environment

Node version: v22.20.0
npm version: 10.9.4
Local ESLint version: v9.39.1
Global ESLint version: -
Operating System: Mac 15.6.1


### What parser are you using?

@typescript-eslint/parser

### What did you do?

We have some default configuration, and try to override some rules.

When overriding `@typescript-eslint/eslint-plugin` rules, we either got error `Could not find plugin "@typescript-eslint" in configuration.` if we don't add this plugin to `plugins`, or we get `Cannot redefine plugin "@typescript-eslint".` if we do add it to `plugins`.

And error message doesn't tell how to fix it.

<details>
<summary>Configuration</summary>

```js
import {feEslint} from '@fe/eslint-config'
import tsEslintPlugin from '@typescript-eslint/eslint-plugin'
import tsParser from '@typescript-eslint/parser'
import jsxA11yPlugin from 'eslint-plugin-jsx-a11y'
import prettierPlugin from 'eslint-plugin-prettier'
import reactPlugin from 'eslint-plugin-react'
import reactHooksPlugin from 'eslint-plugin-react-hooks'
import globals from 'globals'

// eslint-disable-next-line import/no-default-export
export default feEslint({
	ignores: ['node_modules/', 'dist/', 'build/', 'android/', 'ios/', '*.json'],
}).then((config) => [
	...config,
	reactPlugin.configs.flat.recommended,
	reactHooksPlugin.configs.flat.recommended,
	{
		files: ['**/*.{js,mjs,jsx,ts,tsx}'],
		languageOptions: {
			parser: tsParser,
			ecmaVersion: 'latest',
			sourceType: 'module',
			parserOptions: {
				ecmaVersion: 'latest',
				ecmaFeatures: {
					jsx: true,
				},
			},
			globals: {
				__DEV__: true,
			},
		},
		plugins: {
			'@typescript-eslint': tsEslintPlugin, // <---- Commenting / uncommenting this line!!!
			react: reactPlugin,
			'react-hooks': reactHooksPlugin,
			prettier: prettierPlugin,
			'jsx-a11y': jsxA11yPlugin,
		},
		settings: {
			'import/external-module-folders': ['node_modules', 'node_modules/@types'],
			'import/ignore': ['react-native'], // FIX https://github.com/facebook/react-native/issues/28549#issuecomment-622178649
			react: {pragma: 'React', version: 'detect'},
			polyfills: ['Promise', 'requestAnimationFrame'],
		},
		rules: {
			'prettier/prettier': 'error',
			'no-useless-rename': ['error', {ignoreDestructuring: false, ignoreImport: false, ignoreExport: false}],
			'import/namespace': ['error', {allowComputed: true}],
			'react/jsx-max-depth': [1, {max: 7}],
			'jsx-a11y/alt-text': 0,
			'unicorn/filename-case': ['warn', {case: 'snakeCase'}],
			'spaced-comment': ['error', 'always', {exceptions: ['-', '+', '_'], block: {balanced: true}}],
			'no-console': ['error', {allow: ['debug']}],
			'no-restricted-syntax': [
				'error',
				{
					selector: 'ClassDeclaration',
					message: 'Classes are forbidden, see guidelines.',
				},
			],
			'no-unused-vars': 0,
			'@typescript-eslint/no-unused-vars': ['error', {argsIgnorePattern: '^_', caughtErrors: 'all'}],
			'@typescript-eslint/no-var-requires': 0,
			'@typescript-eslint/ban-types': 0,
			'@typescript-eslint/consistent-type-definitions': ['error', 'type'],
			'@typescript-eslint/naming-convention': [
				'error',
				{
					selector: 'typeLike',
					format: ['PascalCase'],
					custom: {regex: '^(I[a-z]|[^I]|IOS)', match: true},
				},
			],
			'import/order': [
				'error',
				{
					'newlines-between': 'always',
					alphabetize: {
						order: 'asc',
						caseInsensitive: true,
					},
				},
			],

			// Disabled from @fe/eslint-config
			'@stylistic/object-curly-spacing': 0,
			'unicorn/prefer-module': 0, // We use require in many places

			// Disabled from react/react-hooks
			'react/display-name': 0,
			'react/react-in-jsx-scope': 0,
			'react-hooks/preserve-manual-memoization': 0,
			'react-hooks/set-state-in-effect': 0,
		},
	},
	{
		files: ['**/*.test.{js,jsx,ts,tsx}', 'tests/**.{js,jsx,ts,tsx}'],
		languageOptions: {
			globals: {
				after: true,
				afterAll: true,
				afterEach: true,
				before: true,
				beforeAll: true,
				beforeEach: true,
				describe: true,
				expect: true,
				it: true,
				jest: true,
				test: true,
			},
		},
	},
	{
		files: ['detox/e2e/**.{js,jsx,ts,tsx}'],
		rules: {
			'import/no-unresolved': 0,
			'no-restricted-syntax': 0,
		},
	},
	{
		files: ['metro.config.js'],
		languageOptions: {
			globals: {
				...globals.node,
			},
		},
	},
])

```
</details>

```js
any ts code
```


### What did you expect to happen?

Either everything should be ok, or we get error message with how to properly fix it.

### What actually happened?

We got error messages in any case.

Also, when commenting ts plugin it shows errors only in .ts files, but when uncommenting - shows errors only in .js config files.

### Link to Minimal Reproducible Example

-

### Participation

- [ ] I am willing to submit a pull request for this issue.

### Additional comments

_No response_

A simulated tool transcript is supplied in support/simulated-tool-response.txt. It is evidence text, not a live tool interface.
