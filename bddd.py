# ==== one_file_mining_game.py ====

from flask import Flask, jsonify, request, render_template_string
import threading, json, os

SAVE_FILE = "save.json"

# ==== Логіка гри ====
class Owner:
    def __init__(self):
        self.balance=1000
        self.cashbox=0
        self.total_income=0

    def add_donation(self, amount):
        fee = amount*0.05
        self.cashbox += fee
        self.balance += amount-fee

owner = Owner()

resources = {
    "Вугілля":{"amount":500,"price":50},
    "Золото":{"amount":50,"price":500},
    "Криптовалюта":{"amount":20,"price":1000},
    "Енергія":{"amount":1000,"price":1}
}

class Equipment:
    def __init__(self,name,count,level,production,energy):
        self.name=name; self.count=count; self.level=level
        self.production=production; self.energy=energy

class Mine:
    def __init__(self): self.equipments=[]
    def add_equipment(self,equipment): self.equipments.append(equipment)
    def produce(self):
        factor=1.0
        total={}
        total_energy=0
        for eq in self.equipments:
            for res,amt in eq.production.items():
                total[res] = total.get(res,0) + amt*eq.count*factor
            total_energy += eq.energy*eq.count
        if total_energy>resources["Енергія"]["amount"]:
            factor_energy = resources["Енергія"]["amount"]/total_energy
            for res in total: total[res]*=factor_energy
            resources["Енергія"]["amount"]=0
        else:
            resources["Енергія"]["amount"]-=total_energy
        for res,qty in total.items():
            resources[res]["amount"]+=qty
        return total

mine = Mine()
mine.add_equipment(Equipment("Машина",2,1,{"Вугілля":50,"Золото":1},50))
mine.add_equipment(Equipment("Майнери",1,1,{"Криптовалюта":2},150))

class Building:
    def __init__(self,name,level,income,energy=0):
        self.name=name; self.level=level; self.income=income; self.energy=energy

class City:
    def __init__(self):
        self.map=[]
    def add_row(self,row): self.map.append(row)
    def collect_income(self):
        total_income = sum(b.income for row in self.map for b in row)
        total_energy = sum(b.energy for row in self.map for b in row)
        resources["Енергія"]["amount"] += total_energy
        owner.balance += total_income
        return {"income":total_income,"energy":total_energy}

city = City()
city.add_row([Building("Житловий",1,20),Building("Фабрика",1,100),Building("Електростанція",1,50)])
city.add_row([Building("Магазин",1,30),Building("Електростанція",1,100),Building("Житловий",1,20)])

# ==== Збереження / Завантаження ====
def save_game():
    data = {
        "owner":{"balance":owner.balance,"cashbox":owner.cashbox,"total_income":owner.total_income},
        "resources":resources
    }
    with open(SAVE_FILE,"w") as f: json.dump(data,f)

def load_game():
    if os.path.exists(SAVE_FILE):
        with open(SAVE_FILE,"r") as f:
            data=json.load(f)
            owner.balance = data["owner"]["balance"]
            owner.cashbox = data["owner"]["cashbox"]
            owner.total_income = data["owner"]["total_income"]
            for res in resources: resources[res]["amount"]=data["resources"][res]["amount"]

load_game()

# ==== Сервер ====
app = Flask(__name__)

INDEX_HTML = """
<!DOCTYPE html>
<html lang="uk">
<head>
<meta charset="UTF-8">
<title>Моя Шахта</title>
<script>
async function updateState(){
  const res = await fetch("/get_state");
  const data = await res.json();
  let html = "<b>Баланс власника:</b> "+data.owner_balance+"₴ | Каса: "+data.cashbox+"₴<br>";
  html += "<b>Ресурси:</b><br>";
  for(let res in data.resources){
    html += res+": "+data.resources[res].amount+"<br>";
  }
  document.getElementById("topbar").innerHTML=html;
}
async function collectProfit(){
  await fetch("/collect_profit");
  updateState();
}
async function donate100(){
  await fetch("/donate",{
    method:"POST",
    headers:{"Content-Type":"application/json"},
    body:JSON.stringify({amount:100})
  });
  updateState();
}
setInterval(updateState,5000);
updateState();
</script>
</head>
<body>
<h1>Проект Шахта</h1>
<div id="topbar"></div>
<button onclick="collectProfit()">Зібрати прибуток</button>
<button onclick="donate100()">Донат 100₴</button>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(INDEX_HTML)

@app.route("/get_state")
def get_state():
    return jsonify({"resources":resources,"owner_balance":owner.balance,"cashbox":owner.cashbox})

@app.route("/collect_profit")
def collect_profit():
    mine.produce()
    income = city.collect_income()
    owner.total_income += income["income"]
    save_game()
    return jsonify({"message":"Прибуток зібрано","income":income,"owner_balance":owner.balance})

@app.route("/donate",methods=["POST"])
def donate():
    data=request.json
    amount=data.get("amount",0)
    owner.add_donation(amount)
    save_game()
    return jsonify({"message":"Донат прийнято","owner_balance":owner.balance,"cashbox":owner.cashbox})

# ==== Автозбір прибутку кожні 60 сек ====
def auto_collect():
    mine.produce()
    city.collect_income()
    save_game()
    threading.Timer(60, auto_collect).start()
auto_collect()

if __name__=="__main__":
    app.run(debug=True)
