const householdSections = [
  {title:"01 / Core sensors", hint:"Four monitoring indicators", fields:[
    {key:"current_a", label:"Pump current", unit:"A", min:0, max:6, step:.05},
    {key:"flow_l_min", label:"Permeate flow", unit:"L/min", min:0, max:3.5, step:.01},
    {key:"pressure_bar", label:"Pressure", unit:"bar", min:0, max:12, step:.1},
    {key:"raw_tds_ppm", label:"Raw-water TDS", unit:"ppm", min:1, max:1200, step:1},
    {key:"output_tds_ppm", label:"Output-water TDS", unit:"ppm", min:0, max:800, step:1},
  ]},
  {title:"02 / Filter history", hint:"Usage since installation", fields:[
    {key:"cumulative_litres", label:"Water produced", unit:"L", min:0, max:20000, step:10},
    {key:"filter_age_days", label:"Filter age", unit:"days", min:0, max:600, step:1},
    {key:"runtime_hours", label:"Pump runtime", unit:"hours", min:0, max:1500, step:1},
  ]},
  {title:"03 / Recent trends", hint:"Change over the last week", fields:[
    {key:"flow_trend_pct_week", label:"Flow change", unit:"% / week", min:-30, max:30, step:.1},
    {key:"current_trend_pct_week", label:"Current change", unit:"% / week", min:-30, max:30, step:.1},
    {key:"pressure_trend_pct_week", label:"Pressure change", unit:"% / week", min:-30, max:30, step:.1},
  ]},
];

const nrelFields = [
  {key:"pressure_bar",label:"Feed pressure",unit:"bar",min:34,max:63,step:.1},
  {key:"feed_flow_l_min",label:"Feed flow",unit:"L/min",min:14,max:27,step:.1},
  {key:"feed_conductivity_ms_cm",label:"Feed conductivity",unit:"mS/cm",min:50,max:62,step:.1},
  {key:"temperature_c",label:"Feed temperature",unit:"°C",min:19,max:21,step:.1},
];

const presets = {
  "Healthy": {current_a:1.5,flow_l_min:1.7,pressure_bar:6.6,raw_tds_ppm:520,output_tds_ppm:34,cumulative_litres:2200,filter_age_days:90,runtime_hours:170,flow_trend_pct_week:-.4,current_trend_pct_week:.2,pressure_trend_pct_week:.1},
  "Fouling": {current_a:2.1,flow_l_min:.93,pressure_bar:8.4,raw_tds_ppm:520,output_tds_ppm:58,cumulative_litres:8500,filter_age_days:310,runtime_hours:610,flow_trend_pct_week:-7.1,current_trend_pct_week:3.2,pressure_trend_pct_week:2.8},
  "Membrane issue": {current_a:1.6,flow_l_min:1.5,pressure_bar:6.6,raw_tds_ppm:520,output_tds_ppm:160,cumulative_litres:9800,filter_age_days:355,runtime_hours:730,flow_trend_pct_week:-1.4,current_trend_pct_week:.5,pressure_trend_pct_week:.4},
  "No flow": {current_a:2.0,flow_l_min:0,pressure_bar:8.1,raw_tds_ppm:520,output_tds_ppm:75,cumulative_litres:8000,filter_age_days:280,runtime_hours:550,flow_trend_pct_week:-20,current_trend_pct_week:4,pressure_trend_pct_week:2},
};

const researchDefaults = {pressure_bar:50,feed_flow_l_min:22,feed_conductivity_ms_cm:55,temperature_c:20};
let simTimer, researchTimer;

function makeFields(targetId, sections) {
  const parent = document.getElementById(targetId);
  parent.innerHTML = sections.map(section => `<div class="field-section"><div class="field-heading"><h3>${section.title}</h3><span>${section.hint}</span></div><div class="field-grid">${section.fields.map(f => `<div class="field"><div class="field-top"><label for="${targetId}-${f.key}">${f.label}</label><span class="unit">${f.unit}</span></div><div class="field-bottom"><input aria-label="${f.label} slider" data-key="${f.key}" data-kind="range" type="range" min="${f.min}" max="${f.max}" step="${f.step}"><input id="${targetId}-${f.key}" aria-label="${f.label} value" data-key="${f.key}" data-kind="number" type="number" min="${f.min}" max="${f.max}" step="${f.step}"></div></div>`).join("")}</div></div>`).join("");
  parent.addEventListener("input", event => {
    if(!event.target.matches("input[data-key]")) return;
    const key=event.target.dataset.key;
    const partner=parent.querySelector(`input[data-key="${key}"][data-kind="${event.target.dataset.kind === "range" ? "number" : "range"}"]`);
    partner.value=event.target.value;
    if(targetId === "sensorFields") {
      document.querySelectorAll(".preset").forEach(b => b.classList.remove("active"));
      clearTimeout(simTimer); simTimer=setTimeout(runSimulation,130);
    } else {
      clearTimeout(researchTimer); researchTimer=setTimeout(runResearch,130);
    }
  });
}

function setValues(parentId, values) {
  const parent=document.getElementById(parentId);
  Object.entries(values).forEach(([key,value]) => parent.querySelectorAll(`input[data-key="${key}"]`).forEach(el => el.value=value));
}

function getValues(parentId) {
  const result={};
  document.querySelectorAll(`#${parentId} input[data-kind="number"]`).forEach(el => result[el.dataset.key]=Number(el.value));
  return result;
}

async function postJson(url, values) {
  const response=await fetch(url,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(values)});
  const data=await response.json();
  if(!response.ok) {
    const detail=Array.isArray(data.detail) ? data.detail.map(e=>`${e.loc.at(-1)}: ${e.msg}`).join("; ") : (data.detail || "Request failed");
    throw new Error(detail);
  }
  return data;
}

async function runSimulation() {
  const note=document.getElementById("resultNote");
  try {
    const result=await postJson("/api/predict",getValues("sensorFields"));
    document.querySelector(".result-panel").className=`result-panel ${result.status}`;
    document.getElementById("statusIcon").textContent={normal:"✓",warning:"!",critical:"×",off:"–"}[result.status];
    document.getElementById("statusTitle").textContent=result.status;
    document.getElementById("statusDescription").textContent={normal:"Readings resemble the healthy simulation examples.",warning:"Something has changed. Check the readings again.",critical:"A serious fault pattern or a physical check was triggered.",off:"No health prediction while the pump is off."}[result.status];
    document.getElementById("rejectionValue").textContent=`${result.salt_rejection_pct.toFixed(1)}%`;
    document.getElementById("confidenceText").textContent=result.status === "off" ? "Not evaluated" : `Top class ${Math.round(result.model_confidence*100)}%`;
    for(const label of ["normal","warning","critical"]) {
      const pct=Math.round((result.probabilities[label]||0)*100);
      document.getElementById(`bar${label[0].toUpperCase()+label.slice(1)}`).style.width=`${pct}%`;
      document.getElementById(`prob${label[0].toUpperCase()+label.slice(1)}`).textContent=`${pct}%`;
    }
    note.className=`note-box ${result.status === "critical" ? "error" : ""}`;
    note.textContent=result.notes.join(" ");
  } catch(error) {
    document.getElementById("statusTitle").textContent="Check inputs";
    document.getElementById("statusDescription").textContent="Some values need correction.";
    note.className="note-box error"; note.textContent=error.message;
  }
}

async function runResearch() {
  try {
    const result=await postJson("/api/nrel-flow",getValues("researchFields"));
    document.getElementById("nrelFlow").textContent=result.predicted_permeate_flow_l_min.toFixed(2);
    document.getElementById("nrelNote").textContent="Expected output for these NREL experimental conditions.";
  } catch(error) {
    document.getElementById("nrelFlow").textContent="—";
    document.getElementById("nrelNote").textContent=error.message;
  }
}

function activateTab(research) {
  document.getElementById("simView").hidden=research;
  document.getElementById("researchView").hidden=!research;
  document.getElementById("simTab").classList.toggle("active",!research);
  document.getElementById("researchTab").classList.toggle("active",research);
  document.getElementById("simTab").setAttribute("aria-selected",String(!research));
  document.getElementById("researchTab").setAttribute("aria-selected",String(research));
  document.querySelector(".topline-right").textContent=research ? "02 / 02 — NREL RESEARCH" : "01 / 02 — SENSOR SIMULATOR";
}

async function init() {
  makeFields("sensorFields",householdSections);
  makeFields("researchFields",[{title:"01 / NREL measurements",hint:"Seawater RO equipment",fields:nrelFields}]);
  setValues("sensorFields",presets.Healthy);
  setValues("researchFields",researchDefaults);
  const presetRoot=document.getElementById("presets");
  Object.entries(presets).forEach(([name,values],index)=>{
    const button=document.createElement("button"); button.type="button"; button.className=`preset ${index===0?"active":""}`; button.textContent=name;
    button.addEventListener("click",()=>{document.querySelectorAll(".preset").forEach(b=>b.classList.remove("active"));button.classList.add("active");setValues("sensorFields",values);runSimulation()});
    presetRoot.append(button);
  });
  document.getElementById("simTab").addEventListener("click",()=>activateTab(false));
  document.getElementById("researchTab").addEventListener("click",()=>activateTab(true));
  try {
    const response=await fetch("/api/model-info"); const info=await response.json();
    document.getElementById("simAccuracy").textContent=`${(info.status_model.accuracy*100).toFixed(1)}%`;
    document.getElementById("simF1").textContent=info.status_model.macro_f1.toFixed(3);
    document.getElementById("criticalRecall").textContent=`${(info.status_model.report.critical.recall*100).toFixed(1)}%`;
    document.getElementById("nrelMae").textContent=`${info.nrel_flow_model.mae_l_min.toFixed(3)} L/min`;
    document.getElementById("nrelR2").textContent=info.nrel_flow_model.r2.toFixed(3);
  } catch(error) { console.error("Could not load model metrics",error); }
  runSimulation(); runResearch();
}

init();
