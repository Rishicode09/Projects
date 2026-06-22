const { getDefaultConfig } = require('expo/metro-config');
const { withNativeWind } = require('nativewind/metro');

const config = getDefaultConfig(__dirname);

// NativeWind v4 processes Tailwind via Metro, using global.css as the input.
module.exports = withNativeWind(config, { input: './global.css' });
