module.exports = {
  root: true,
  parser: '@typescript-eslint/parser',
  parserOptions: { ecmaVersion: 2021, sourceType: 'module', ecmaFeatures: { jsx: true } },
  plugins: ['@typescript-eslint'],
  extends: ['eslint:recommended', 'plugin:@typescript-eslint/recommended'],
  env: { 'react-native/react-native': true, node: true, jest: true, es2021: true },
  ignorePatterns: ['node_modules/', 'dist/', 'web-build/', 'babel.config.js', 'metro.config.js'],
  rules: {
    '@typescript-eslint/no-unused-vars': ['warn', { argsIgnorePattern: '^_' }],
    '@typescript-eslint/consistent-type-imports': 'warn',
    'no-console': ['warn', { allow: ['warn', 'error'] }],
  },
};
