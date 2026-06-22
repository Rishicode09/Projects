module.exports = function (api) {
  const isTest = api.env('test');
  api.cache.using(() => process.env.NODE_ENV);
  return {
    // NativeWind's babel preset is only needed for the running app; the Jest
    // suite covers pure logic, so we skip it under test to avoid coupling tests
    // to the styling toolchain.
    presets: isTest
      ? ['babel-preset-expo']
      : ['babel-preset-expo', 'nativewind/babel'],
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
    ],
  };
};
