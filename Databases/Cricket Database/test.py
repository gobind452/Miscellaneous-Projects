from flask import Flask, redirect, url_for, request,render_template
import connect 

app = Flask(__name__) # Constructor

@app.route('/home',methods=['POST','GET'])
def home():
	return render_template('home.html')

@app.route('/reset/<message>',methods=['POST','GET'])
def reset(message):
	return render_template('home.html',message=message)

@app.route('/result',methods = ['POST','GET']) 
def result():
	parameter = dict(request.form) # Creates a dict of the form results
	result = connect.executeGeneralSelectQuery(parameter) # Give it to the psycopg2 code
	return render_template('hello.html',result = result) # Give the answer to the template page 

@app.route('/player/<Id>',methods = ['GET'])
def player(Id):
	name,country,result_test,result_odi,result_t20 = connect.executeSpecificQuery(Id)
	similar_players = connect.similarPlayers(Id)
	return render_template('player.html',Id=Id,result_test = result_test,result_odi=result_odi,result_t20=result_t20,name = name,country = country,similar_players= similar_players)

@app.route('/search',methods = ['GET'])
def search():
	return render_template('search.html')

@app.route('/add', methods = ['POST','GET'])
def add():
	if request.method == 'GET':
		return render_template('add.html')
	elif request.method == 'POST':
		parameters = dict(request.form)
		if parameters['name'] == '':
			return redirect(url_for('reset', message = "Name not entered"))
		if parameters['country'] == '':
			return redirect(url_for('reset', message = "Country not entered"))
		Id = connect.addPlayer(parameters)
		return redirect(url_for('added',Id = Id,name=parameters['name'],country=parameters['country']))

@app.route('/added/<Id>/<name>/<country>',methods = ['POST','GET'])
def added(Id,name,country):
	if request.method == 'GET':
		return render_template('added.html',Id = Id, name = name, country = country)
	elif request.method == 'POST':
		parameters = dict(request.form)
		parameters['Id'] = Id
		connect.executeGeneralInsertQuery(parameters)
		return redirect(url_for('home'))

@app.route('/delete/<Id>', methods=['GET'])
def delete(Id):
	connect.deletePlayer(Id)
	return redirect(url_for('reset',message="Success"))

@app.route('/prompt/<page>',methods=['GET'])
def prompt(page):
	return render_template('prompt.html',page=page)

@app.route('/update/<Id>', methods=['GET','POST'])
def update(Id):
	if request.method == 'GET':
		return render_template('update.html',Id = Id)
	elif request.method == 'POST':
		parameters = dict(request.form)
		parameters['Id'] = Id 
		connect.updateGeneral(parameters)
		return redirect(url_for('player',Id =Id))

@app.route('/country',methods=['GET','POST'])
def country():
	if request.method == 'GET':
		parameters = dict(request.args)
		if len(parameters.keys()) == 0:
			return render_template('country.html')
		else:
			result,bat,ball = connect.fillInfo(parameters)
			return render_template('country_open.html',result = result,country = parameters['country'],game = parameters['game'],bat=bat,ball=ball)
		
if __name__ == '__main__':
   app.run()