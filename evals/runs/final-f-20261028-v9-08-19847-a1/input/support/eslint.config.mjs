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