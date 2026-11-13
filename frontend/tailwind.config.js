export default{
  content:["./index.html","./src/**/*.{js,jsx}"],
  theme:{
    extend:{
      colors:{
        ink:"hsl(var(--ink) / <alpha-value>)",
        mute:"hsl(var(--mute) / <alpha-value>)",
        paper:"hsl(var(--paper) / <alpha-value>)",
        surface:"hsl(var(--surface) / <alpha-value>)",
        rule:"hsl(var(--rule) / <alpha-value>)",
        bull:"hsl(var(--bull) / <alpha-value>)",
        bear:"hsl(var(--bear) / <alpha-value>)",
        flat:"hsl(var(--flat) / <alpha-value>)",
        mark:"hsl(var(--mark) / <alpha-value>)",
        "on-mark":"hsl(var(--on-mark) / <alpha-value>)"
      },
      fontFamily:{
        serif:["Source Serif 4","Georgia","serif"],
        sans:["IBM Plex Sans","system-ui","sans-serif"],
        mono:["IBM Plex Mono","ui-monospace","monospace"]
      }
    }
  },
  plugins:[]
}
