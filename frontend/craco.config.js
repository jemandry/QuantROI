const webpack = require('webpack');

module.exports = {
  webpack: {
    configure: (webpackConfig) => {
      webpackConfig.resolve.fallback = {
        ...webpackConfig.resolve.fallback,
        crypto: require.resolve('crypto-browserify'),
        stream: require.resolve('stream-browserify'),
        assert: require.resolve('assert'),
        https: require.resolve('https-browserify'),
        os: require.resolve('os-browserify'),
        url: require.resolve('url'),
        path: require.resolve('path-browserify'),
        process: require.resolve('process/browser'),
      };
      
      webpackConfig.resolve.extensionAlias = {
        '.js': ['.js', '.ts', '.tsx'],
        '.mjs': ['.mjs', '.js'],
      };
      
      webpackConfig.resolve.alias = {
        ...webpackConfig.resolve.alias,
        'process/browser': require.resolve('process/browser'),
      };
      
      webpackConfig.plugins = [
        ...webpackConfig.plugins,
        new webpack.ProvidePlugin({
          process: 'process/browser',
          Buffer: ['buffer', 'Buffer'],
        }),
      ];
      
      return webpackConfig;
    },
  },
};
