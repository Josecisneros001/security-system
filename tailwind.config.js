const colors = require('tailwindcss/colors');

module.exports = {
  purge: {
    content: [
      './**/*.html',
    ],
    enabled: process.env.NODE_ENV === 'production'
  },
  darkMode: false, // or 'media' or 'class'
  theme: {
    colors: {
      black: colors.black,
      white: colors.white,
      gray: colors.coolGray,
      red: colors.red,
      yellow: colors.amber,
      green: colors.emerald,
      blue: colors.blue,
      indigo: colors.indigo,
      purple: colors.violet,
      pink: colors.pink,
      yellow2: '#fff700',
      primaryColor: '#c9ebe7',
      primaryColorT: '#69afd8',
      secondaryColor: '#484848',
      transparent: 'transparent',
      current: 'currentColor',
    },
    extend: {
      width: {
        '84': '21rem',
        '88': '22rem',
        '92': '23rem',
        '1/7': '14.2857143%',
        '2/7': '28.5714286%',
        '3/7': '42.8571429%',
        '4/7': '57.1428571%',
        '5/7': '71.4285714%',
        '6/7': '85.7142857%',
      },
      maxWidth: {
        '1/4': '25%',
        '1/3': '33%',
        '1/2': '50%',
        '3/4': '75%',
      },
      minWidth: {
        'sm': '300px',
        'md': '350px',
        'md-1/2': '175px',
        'lg': '620px',
        'lg-1/2': '310px',
        '1/7': '14.28%',
        '1/4': '25%',
        '1/3': '33%',
        '1/2': '50%',
        '3/4': '75%',
      },
      screens: {
        'xsm': '425px',
      },
    },
  },
  variants: {
    extend: {},
  },
  plugins: [],
}
