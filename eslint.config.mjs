import tseslint from 'typescript-eslint';

export default tseslint.config(
  {ignores:['**/.next/**','**/node_modules/**']},
  ...tseslint.configs.recommended,
  {rules:{'@typescript-eslint/no-unused-vars':'off','@typescript-eslint/no-empty-object-type':'off'}},
);
