from flask import Flask, request, jsonify
from pulp import LpProblem, LpVariable, LpContinuous,LpMinimize,value,lpSum
import numpy as np


app = Flask(__name__)

def calculate_nutrition_secondary(ingredient,result):
    starch = 100 - (
        ingredient['Crude protein'] +
        ingredient['Crude fat'] +
        ingredient['Crude ash'] +
        ingredient['Moisture'] +
        ingredient['Crude fiber']
    )
    if starch < 0:
        starch = 0

    metabolizable_energy = 10 * (
        (3.5 * ingredient['Crude protein']) +
        (8.5 * ingredient['Crude fat']) +
        (3.5 * starch)
    )
    
    methionine_cystine = ingredient['Methionine'] + ingredient['Cystine']
    phenylalanine_tyrosine = ingredient['Phenylalanine'] + ingredient['Tyrosine']
    omega6_omega3_ratio = (ingredient['Linoleic acid'] + ingredient['Arachidonic Acid']) / (ingredient['Alpha linolenic acid'] + ingredient['DHA'] + ingredient['EPA'])
    calcium_Phosphorus_ratio = ingredient['Calcium'] / ingredient['Phosphorus']
    vitaminc = ingredient['Vitamin C']*10
    total_omega_3 =  ingredient['Alpha linolenic acid'] + ingredient['DHA'] + ingredient['EPA']

    for key,value1 in result.items():
        if key != 'name':
            if key == 'Metabolizable energy':
                result[key] += metabolizable_energy
            elif key == 'Starch':
                result[key] += starch
            elif key == 'Methionine+Cystine':
                result[key] += methionine_cystine
            elif key == 'Phenylalanine+Tyrosine':
                result[key] += phenylalanine_tyrosine
            elif key == 'Omega6/Omega3 ratio':
                result[key] += omega6_omega3_ratio
            elif key == 'Calcium/Phosphorus ratio':
                result[key] += calcium_Phosphorus_ratio
            elif key == 'Vitamin C':
                result[key] += vitaminc
            elif key == 'Total Omega 3':
                result[key] += total_omega_3
            for key2,value2 in ingredient.items():
                if key == key2:
                    result[key] += value2 

    return result

def linear_pulp(average_limit, min_limit, max_limit, results):
    ingredientsdata = []

    for result in results:
        index = 0
        ingredientsdata.append([float(result[key]) for key in result.keys() if key != "name"])
        for key, value1 in result.items():
            if key != 'name' and key == 'Moisture':
                index_of_water = index-1
            elif key != 'name' and key != 'Price':
                index_of_price = index
            index += 1


    model = LpProblem("Balanced_Diet_Problem", LpMinimize)

    variables = []
    for i in range(len(results)):
        variable = LpVariable(f"{results[i]['name']}", 0, None, LpContinuous)
        variables.append(variable)

    model += sum([ingredientsdata[i][index_of_price]*variables[i] for i in range(len(ingredientsdata))]), "Total_Cost_of_Diet"

    for i in range(len(ingredientsdata[0])):
        if i != index_of_water and i != index_of_price:
            lhs = sum(ingredientsdata[j][i] * variables[j] for j in range(len(ingredientsdata)))
            rhs = sum(ingredientsdata[j][index_of_water] * variables[j] for j in range(len(ingredientsdata)))
            model += rhs >= 1
            model += 100 * lhs == average_limit[i] * rhs

    model += lpSum(variables) == 100

    model.solve()
    res = []
    for v in model.variables():
        print(v.name, "=", v.varValue)
        res.append(v.varValue)
    print("Sum of V.VarValue = ",sum(res))
    print("Value of Objective Function = ", value(model.objective))

    ingred_DM = []
    water_value = sum(ingredientsdata[j][index_of_water] * res[j] for j in range(len(ingredientsdata)))
    for i in range (len(ingredientsdata[0])):
        if (i == index_of_water):
            sum_nutrition = 0
            ingred_DM.append(sum_nutrition)
        if (i != index_of_water):
            sum_nutrition = 100*(sum(ingredientsdata[j][i] * res[j] for j in range(len(ingredientsdata))))/water_value
            ingred_DM.append(sum_nutrition)
    
    for i in range(len(ingredientsdata[0])):
        if (i != index_of_price and i != index_of_water):
            print(ingred_DM[i])
            print(min_limit[i])
            print(max_limit[i])
            
            if (ingred_DM[i] > max_limit[i]):
                print(i)
                print("max limit exceeded")
            if (ingred_DM[i] < min_limit[i]):
                print(i)
                print("min limit exceeded")
            print("-------------------")

    freshNutrient = []
    for i in range (len(ingredientsdata[0])):
        if (i == index_of_water):
            freshNutrient.append(water_value)
        if (i != index_of_water):
            sum_nutrition = 100*(sum(ingredientsdata[j][i] * res[j] for j in range(len(ingredientsdata))))
            freshNutrient.append(sum_nutrition)

    return res, freshNutrient

@app.route('/algorithmA', methods=['POST'])
def linear_algorithm():
    try:

        data_json = request.get_json()
        ingredients = data_json["ingredients"]
        limitmin = data_json["limit"][0]
        limitmax = data_json["limit"][1]
        limitmean = data_json["limit"][2]
        
        results = []
        for ingredient in ingredients:
            result = {'name': ingredient['name']} 
            for key,value1 in limitmin.items():
                if key != 'name':
                    result[key] = 0 
            
            result = calculate_nutrition_secondary(ingredient,result)
            results.append(result)

        
        average_limit = [float(value1) for key,value1 in limitmean.items() if key != "name"]
        min_limit = [float(value1) for key,value1 in limitmin.items() if key != "name"]
        max_limit = [float(value1) for key,value1 in limitmax.items() if key != "name"]
        coefficient,nutrientList = linear_pulp(average_limit, min_limit, max_limit, results)
        print(sum(coefficient))
        #เอาสัมประสิทธิ์ที่ได้มาใส่ใน data_json
        #เอาสารอาหารที่รวมได้จากสัมประสิทธิ์*สารอาหารส่งกลับไปให้ใน data_json
        ingredientList = []    
        for ingredient, amount in zip(ingredients, coefficient):
            result = {'name': ingredient['name'], 'amount': amount}
            ingredientList.append(result)
        print(ingredientList)

        freshNutrientList = []  
        for key, value2 in limitmin.items():
            if key != 'name':
                freshNutrient = {'nutrientname': key, 'amount': 0}
                freshNutrientList.append(freshNutrient)
        
        for nutrients, amounts in zip(freshNutrientList, nutrientList):
            nutrients['amount'] = amounts
        print(freshNutrientList)

        recipes = []
        recipes.append({"ingredientList": ingredientList, "freshNutrient": freshNutrientList})

        print(recipes)
        return jsonify({"petrecipes": recipes}), 200


    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({'error': 'Internal Server Error'}), 500

if __name__ == '__main__':
    app.run(port=3000)
