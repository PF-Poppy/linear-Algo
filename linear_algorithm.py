from flask import Flask, request, jsonify
from scipy.optimize import minimize
import numpy as np
import random


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
    if ingredient['Alpha linolenic acid'] + ingredient['DHA'] + ingredient['EPA'] == 0:
        omega6_omega3_ratio = 0
    else:
        omega6_omega3_ratio = (ingredient['Linoleic acid'] + ingredient['Arachidonic acid']) / (ingredient['Alpha linolenic acid'] + ingredient['DHA'] + ingredient['EPA'])
    if ingredient['Phosphorus'] == 0:
        calcium_Phosphorus_ratio = 0
    else:
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

def check_nutrition(ingredient,limitmin,limitmax,index_price,index_water):
    maxx = 0
    minn = 0
    minindex = []
    maxindex = []
    #print("-------------------")
    for i in range(len(ingredient)):
        if (i != index_price and i != index_water):
            #print("ingredient = ",ingredient[i])
            #print("limitmin = ",limitmin[i])
            #print("limitmax = ",limitmax[i])
            
            if (ingredient[i] > limitmax[i]):
                #print("index = ",i)
                #print("max limit exceeded")
                maxindex.append(i)
                maxx += 1
            if (ingredient[i] < limitmin[i]):
                #print("index = ",i)
                #print("min limit exceeded")
                minindex.append(i)
                minn += 1
            #print("-------------------")
    print("minn = ",minn)        
    print("maxx = ",maxx)
    print("all_index = ",len(ingredient))
    if (maxx == 0 and minn == 0):
        return 0,minindex,maxindex
    return 1,minindex,maxindex

def some_new_value(wantvalue):
    return random.uniform(5, wantvalue)

def objective(x, average_limit, max_limit, min_limit, ingredientsdata, index_of_water, index_of_price):
    for i in range(len(average_limit)):
        if i != index_of_water and i != index_of_price:
            numerator = sum(ingredientsdata[j][i] * x[j] for j in range(len(ingredientsdata)))/100
            denominator = sum(ingredientsdata[j][index_of_water] * x[j] for j in range(len(ingredientsdata)))/100
            predicted_res = 100 * numerator / (100 - denominator)
            if not (min_limit[i] <= predicted_res <= max_limit[i]):
                x = []
                for i in range(len(ingredientsdata)):
                    if (i == 0):
                        x.append(some_new_value(100))
                    else:
                        remaining_sum = 100 - sum(x)
                        x.append(some_new_value(remaining_sum))
                return sum(x) - 100
    return sum(x) - 100

def constraint(x):
    return sum(x) - 100
    
def find_initial_x(average_limit, ingredientsdata, index_of_water, index_of_price, min_limit, max_limit):
    num_ingredients = len(ingredientsdata)

    #x0 = [(100/len(ingredientsdata)) for _ in range(len(ingredientsdata))]
    x0 = []
    for i in range(len(ingredientsdata)):
        if (i == 0):
            x0.append(some_new_value(100))
            #x0.append(100/len(ingredientsdata))
        else:
            remaining_sum = 100 - sum(x0)
            x0.append(some_new_value(remaining_sum))

    def objective_for_x0(x0):
        num_ingredients = len(ingredientsdata)

        # Ensure sum(x) == 100
        if sum(x0) != 100:
            return np.inf

        # Calculate predicted_res values
        predicted_res_values = []
        for i in range(len(average_limit)):
            if i != index_of_water and i != index_of_price:
                numerator = sum(ingredientsdata[j][i] * x0[j] for j in range(num_ingredients))/100
                denominator = sum(ingredientsdata[j][index_of_water] * x0[j] for j in range(num_ingredients)) / 100
                predicted_res = 100 * numerator / (100 - denominator)
                predicted_res_values.append(predicted_res)

        # Calculate the difference between predicted_res and average_limit
        diff_values = [abs(predicted_res - avg_limit) for predicted_res, avg_limit in zip(predicted_res_values, average_limit)]
        # Sum of differences as the objective
        return sum(diff_values)

    result = minimize(
        objective_for_x0,
        x0,
        constraints=[
            {'type': 'eq', 'fun': constraint},  # sum(x) == 100
            {'type': 'ineq', 'fun': lambda x: x - 0},  # x[i] >= 0
            {'type': 'ineq', 'fun': lambda x: 100 - x},  # x[i] <= 100
        ],
        bounds=[(0, 100)] * num_ingredients,
        options={'maxiter': 2000},
        method='Nelder-Mead',
    )

    print(result.message)

    if result.success:
        return result.x
    else:
        print("Optimization failed to find a suitable initial x0. Using default x0.")
        return x0

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

        ingredientsdata = []
        index_of_water = 0
        index_of_price = 0
        for result in results:
            index = 0
            ingredientsdata.append([float(result[key]) for key in result.keys() if key != "name"])
            for key, value1 in result.items():
                if key != 'name' and key == 'Moisture':
                    index_of_water = index-1
                elif key != 'name' and key != 'Price':
                    index_of_price = index
                index += 1

        x0 = find_initial_x(average_limit, ingredientsdata, index_of_water, index_of_price, min_limit, max_limit)
        print("Before optimization: x =", x0)

        solution = minimize(
            objective,
            x0,
            args=(average_limit, max_limit, min_limit, ingredientsdata, index_of_water, index_of_price),
            constraints=[
                {'type': 'eq', 'fun': constraint},  # รวมค่า x เท่ากับ 100
                {'type': 'ineq', 'fun': lambda x: x - 0},  # x แต่ละตัวมีค่ามากกว่าหรือเท่ากับ 0
                {'type': 'ineq', 'fun': lambda x: 100 - x}  # x แต่ละตัวมีค่าไม่เกิน 100
            ],
            bounds=[(0, 100)] * len(ingredientsdata),  # กำหนดขอบเขตของ x
            options={'maxiter': 1000},
            method='trust-constr',
        )
        print("After optimization: x =", solution.x)

        #coefficient = [60,40]
        coefficient = []
        for i in range(len(solution.x)):
            #coefficient.append(solution.x[i])  
            coefficient.append(round(solution.x[i], 3))
        print("Sum of coefficient = ",sum(coefficient))
        ingred_DM = []
        water_value = sum(ingredientsdata[j][index_of_water] * coefficient[j] for j in range(len(ingredientsdata)))/100
        for i in range (len(ingredientsdata[0])):
            if (i == index_of_water):
                sum_nutrition = 0
                ingred_DM.append(sum_nutrition)
            if (i != index_of_water):
                numerator = sum(ingredientsdata[j][i] * coefficient[j] for j in range(len(ingredientsdata)))/100
                sum_nutrition = 100*(numerator)/(100-water_value)
                ingred_DM.append(sum_nutrition)
        ingred_DM[6] = 100-(ingred_DM[1]+ingred_DM[2]+ingred_DM[3]+ingred_DM[4]+ingred_DM[5])
        ingred_DM[0] = 10*((3.5*ingred_DM[2])+(8.5*ingred_DM[3])+(3.5*ingred_DM[6]))
        #print("ingred_DM = ",ingred_DM)

        checkingnutrition,minindex,maxindex = check_nutrition(ingred_DM,min_limit,max_limit,index_of_price,index_of_water)
        if (checkingnutrition == 0):
            print("Nutrition is in range")
        else:
            print("Nutrition is not in range")

        freshNutrient = []
        for i in range (len(ingredientsdata[0])):
            sum_nutrition = 0
            if (i == index_of_water):
                freshNutrient.append(water_value)
            if (i != index_of_water):
                sum_nutrition = sum(ingredientsdata[j][i] * coefficient[j] for j in range(len(ingredientsdata)))/100
                freshNutrient.append(sum_nutrition)
        freshNutrient[6] = 100-(freshNutrient[1]+freshNutrient[2]+freshNutrient[3]+freshNutrient[4]+freshNutrient[5])
        freshNutrient[0] = 10*((3.5*freshNutrient[2])+(8.5*freshNutrient[3])+(3.5*freshNutrient[6]))
        #print("freshNutrient = ",freshNutrient)

        ingredientList = []    
        for ingredient, amount in zip(ingredients, coefficient):
            result = {'name': ingredient['name'], 'amount': amount}
            ingredientList.append(result)
        #print(ingredientList)

        freshNutrientList = []  
        for key, value2 in limitmin.items():
            if key != 'name':
                freshNutrients = {'nutrientname': key, 'amount': 0}
                freshNutrientList.append(freshNutrients)

        for nutrients, amounts in zip(freshNutrientList, freshNutrient):
            nutrients['amount'] = amounts
        #print(freshNutrientList)

        print("maxindex = ",maxindex)
        for i in range(len(maxindex)):
            indexmax = 0
            for key, value1 in limitmin.items():
                if key != 'name':
                    if indexmax == maxindex[i]:
                        print("nutrientname = ",key)
                    indexmax += 1
        print("-------------------")
        print("minindex = ",minindex)
        for i in range(len(minindex)):
            indexmin = 0
            for key, value1 in limitmin.items():
                if key != 'name':
                    if indexmin == minindex[i]:
                        print("nutrientname = ",key)
                    indexmin += 1

        recipes = []
        recipes.append({"ingredientList": ingredientList, "freshNutrient": freshNutrientList})
        #print(recipes)
        return jsonify({"petrecipes": recipes}), 200

    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({'error': 'Internal Server Error'}), 500

if __name__ == '__main__':
    app.run(port=3000)
