module.exports = function (api) {
  // NODE_ENV-keyed cache so the test/app preset choice below is respected.
  api.cache.using(() => process.env.NODE_ENV);
  const isTest = api.env('test');
  return {
    // The Jest suite covers pure logic and renders no styled components, so it
    // skips NativeWind's transform; the app build uses the full v4 setup.
    presets: isTest
      ? ['babel-preset-expo']
      : [['babel-preset-expo', { jsxImportSource: 'nativewind' }], 'nativewind/babel'],
    plugins: [
      [
        'module-resolver',
        {
          root: ['./'],
          alias: {
            '@': './src',
          },
        },
      ],
      // Must be listed last. Required by react-native-reanimated, which
      // NativeWind v4 depends on internally.
      'react-native-reanimated/plugin',
    ],
  };
};
