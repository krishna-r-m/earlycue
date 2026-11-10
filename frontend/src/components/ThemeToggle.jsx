import Segmented from "./Segmented.jsx"

const options=[
  {value:"light",label:"Light"},
  {value:"dark",label:"Dark"}
]

export default function ThemeToggle({theme,onchange}){
  return <Segmented label="Colour theme" options={options} value={theme} onchange={onchange}/>
}
