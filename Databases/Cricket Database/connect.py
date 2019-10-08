import psycopg2
import json

conn = psycopg2.connect(database="project1",user="gobind",password="gobind610")
cursor = conn.cursor()

metadata = {}

with open('metadata.json') as fp:
	metadata = json.load(fp)

def separateParameters(parameters,way):
	separated = {}
	separated['test'] = {}
	separated['odi'] = {}
	separated['t20'] = {}
	keys = list(parameters.keys())
	for e in keys:
		temp = e.split('/')
		temp1 = temp[0].split('_')
		if temp[0] not in separated[temp1[0]].keys() and parameters[e] != '':
			separated[temp1[0]][temp[0]] = {}
			separated[temp1[0]][temp[0]][temp[1]] = parameters[e]
		elif temp[0] in separated[temp1[0]].keys() and parameters[e] != '':
			separated[temp1[0]][temp[0]][temp[1]] = parameters[e]
	if way == 0:
		for e in separated.keys():
			check = e+'_career'
			if check not in separated[e].keys():
				separated[e][check] = {}
	return separated

def createSubquery(parameters):
	keys = list(parameters.keys())
	if len(keys) == 1: # If no parameters
		if len(parameters[keys[0]].keys()) == 0:
			return '',''
	career_table = ''
	for e in keys:
		if e.split('_')[1] == 'career': # Finding the format
			career_table = e 
			break
	query = "(SELECT "+career_table+".id FROM "
	for i in range(len(keys)):
		query = query + keys[i] + int((i+1)!= len(keys))*","
	query = query + " WHERE "
	for i in range(len(keys)-1):
		query = query + keys[i]+".id = "+keys[i+1]+".id AND " # Joining on id 
	for i in range(len(keys)): # Cleaning Up
		if len(list(parameters[keys[i]].keys())) == 0:
			del keys[i]
	for i in range(len(keys)): # Processing atoms
		temp = list(parameters[keys[i]].keys())
		for j in range(len(temp)):
			query = query + processAtom(keys[i],temp[j],parameters[keys[i]][temp[j]]) + int((i+1)!=len(keys) or (j+1)!=len(temp))*" AND "
	new_career = career_table.split('_')[0]
	query = query + ") AS " + new_career
	return new_career,query

def processAtom(prekey,key,value):
	temp = value.split('-')
	if len(temp)>2:
		raise ValueError('Bad Range')
	if len(temp)>1:
		if metadata[prekey][key] == 0:
			raise ValueError('Bad Input')
		if value[-1] == '-':
			part = prekey + "." + key + " >= " + temp[0]
		elif value[0] == '-':
			part = prekey + "." + key + " <= " + temp[1]
		else:
			part = prekey + "." + key + " >= " + temp[0] + " AND " + prekey + "." + key + " <= " + temp[1]
		return part 
	else:
		part = prekey + "." + key + " = " + temp[0]
		return(part)

def executeGeneralSelectQuery(parameters): # Simple select query 
	name = parameters['name']
	country = parameters['country']
	del parameters['name']
	del parameters['country']
	check = (name != '' or country != '')
	parameters = separateParameters(parameters,0)
	sub_queries = {}
	keys = list(parameters.keys())
	for e in keys:
		put,x = createSubquery(parameters[e])
		if x != '':
			sub_queries[put] = x
	if len(sub_queries.keys()) == 0:
		if check == 0:
			return [('No Restriction','Please fill some parameters')]
		else:
			query = "SELECT id,name,country FROM player_names WHERE "+ int(name!='')*("name ILIKE \'%"+name+"%\'") + int(name!='')*int(country!='')*(" AND") + int(country!='')*(" LOWER(player_names.country) = LOWER(\'"+country+"\')")
			cursor.execute(query)
			answer = cursor.fetchall()
			return answer
	formats = list(sub_queries.keys())
	query = "SELECT player_names.id, player_names.name,player_names.country FROM player_names" + int(len(formats)>0)*","
	for i in range(len(formats)):
		query = query + sub_queries[formats[i]] + int((i+1)!=len(formats))*", "
	query = query + int(len(formats)>0 or check)*" WHERE "
	formats.append('player_names')
	if name != '':
		query = query +"player_names.name ILIKE \'%" + name + "%\'" + int(country!='' or len(formats)>1)*" AND "
	if country!='':
		query = query + "LOWER(player_names.country) = LOWER(\'"+country+"\')" + int(len(formats)>1)*" AND "
	for j in range(len(formats)-1):
		query = query + formats[j] + ".id = " + formats[j+1] + ".id" + int((j+2) != len(formats))*" AND "
	cursor.execute(query)
	answer = cursor.fetchall()
	return answer

def addPlayer(parameters):
	query = "INSERT INTO player_names(name,country) VALUES (\'"+str(parameters['name'])+"\',\'"+str(parameters['country'])+"\')"
	cursor.execute(query)
	conn.commit()
	query = "SELECT id FROM player_names ORDER BY Id DESC LIMIT 1"
	cursor.execute(query)
	answer = cursor.fetchall()[0][0]
	return answer

def executeGeneralInsertQuery(parameters):
	Id = parameters['Id']
	del parameters['Id']
	parameters = separateParameters(parameters,1)
	ref = ['test','odi','t20']
	for game in ref:
		keys = list(parameters[game].keys())
		for e in keys:
			query = "INSERT INTO " + e + "(id,"
			columns = list(parameters[game][e].keys())
			for i in range(len(columns)):
				query = query + columns[i]+int((i+1)!=len(columns))*","
			query = query + ") VALUES(" + str(Id)+","
			for i in range(len(columns)):
				query = query + parameters[game][e][columns[i]] + int((i+1)!=len(columns))*","
			query = query + ")"
			cursor.execute(query)
			conn.commit()
	return 

def fix(table,result):
	temp = {}
	columns = list(metadata[table].keys())
	columns.remove('id')
	for i in range(len(columns)):
		if result[i] is not None:
			temp[columns[i]] = result[i]
	return temp

def executeSpecificQuery(Id):
	query = "SELECT name,country FROM player_names WHERE id = "+str(Id)
	cursor.execute(query)
	answer = cursor.fetchall()
	name = answer[0][0]
	country = answer[0][1]
	result = {}
	result['test'] = {}
	result['odi'] = {}
	result['t20'] = {}
	for e in metadata.keys():
		game = e.split('_')[0]
		suffix = e.split('_')[1]
		if game in result.keys() and suffix != 'part':
			result[game][e] = {}
	for game in result.keys():
		for table in result[game].keys():
			query = "SELECT * FROM "+table+" WHERE id = " + str(Id)
			cursor.execute(query)
			print(query)
			answer = list(cursor.fetchall())
			if len(answer)!=0:
				answer = list(answer[0])
				answer.remove(int(Id))
				result[game][table].update(fix(table,answer))
	return name,country,result['test'],result['odi'],result['t20']

def deletePlayer(Id):
	query = "DELETE FROM player_names WHERE id = "+ str(Id)
	cursor.execute(query)
	conn.commit()
	return 

def constraintCheck(table,Id):
	query = "SELECT id FROM "+table+" WHERE id = "+str(Id)
	cursor.execute(query)
	answer = list(cursor.fetchall())
	if len(answer) == 0:
		query = "INSERT INTO "+table+"(id) VALUES("+Id+")"
		cursor.execute(query)
		conn.commit()
		return

def updateGeneral(parameters):
	name = parameters['name']
	country = parameters['country']
	Id = parameters['Id']
	del parameters['name']
	del parameters['country']
	del parameters['Id']
	parameters = separateParameters(parameters,1)
	ref = ['test','odi','t20']
	for game in ref:
		keys = list(parameters[game].keys())
		for e in keys:
			constraintCheck(e,Id)
			query = "UPDATE "+ e + " SET "
			columns = list(parameters[game][e].keys())
			for i in range(len(columns)):
				query = query + columns[i]+" = " + parameters[game][e][columns[i]] + int((i+1)!=len(columns))*","
			query = query + " WHERE id = " + str(Id)
			cursor.execute(query)
			conn.commit()
	query = ""
	check = (name=='' and country == '')
	if name !='':
		query = "UPDATE player_names SET name = \'"+ str(name) + "\'"+int(country!='')*","
	if country!='':
		query = query + int(name=='')*"UPDATE player_names SET " + " country = \'"+str(country) + "\'" 
	if check ==0:
		query = query + " WHERE id = "+str(Id)
		cursor.execute(query)
		conn.commit()
	return 

def similarPlayers(Id):
	query = "SELECT player_names.name,temp.id FROM (select id, sum(num) AS num from( select id2 as id, number_partnerships as num from odi_part where id1 = 45 union select id1 as id, number_partnerships as num from odi_part as part where id2 = 45 union select id2 as id, number_partnerships as num from t20_part as part where id1 = 45 union select id1 as id, number_partnerships as num from t20_part as part where id2 = 45 union select id2 as id, number_partnerships as num from test_part as part where id1 = 45 union select id1 as id, number_partnerships as num from test_part as part where id2 = 45 ) as foo group by id order by num desc limit 5) as temp,player_names WHERE temp.id = player_names.id ORDER BY temp.num DESC;"
	query = query.replace('45',str(Id))
	cursor.execute(query)
	result = cursor.fetchall()
	return result

def fillInfo(parameters):
	country = parameters['country']
	game = parameters['game']
	result = {}
	queries = {"Max Runs": "select name, runs from odi_comp_bat where LOWER(country) = LOWER('India') and runs = (select max(runs) from odi_comp_bat where LOWER(country) = LOWER('India'))","Maximum Average":"select name, average from odi_comp_bat where LOWER(country) = LOWER('India') and average = (select max(average) from odi_comp_bat where LOWER(country) = LOWER('India') and innings>100)","Highest Score":"select name, highest_score as score from odi_comp_bat where LOWER(country) = LOWER('India') and highest_score = (select max(highest_score) from odi_comp_bat where LOWER(country) = LOWER('India'))","Most Wickets":"select name, wickets from odi_comp_ball where LOWER(country) = LOWER('India') and wickets = (select max(wickets) from odi_comp_ball where LOWER(country) = LOWER('India'))","Least Bowling Avg":"select name, bowling_avg from odi_comp_ball where LOWER(country) = LOWER('India') and bowling_avg = (select min(bowling_avg) from odi_comp_ball where LOWER(country) = LOWER('India') and innings>100)"}
	for e in queries.keys():
		query = queries[e].replace('odi',game)
		query = query.replace('India',country)
		if game == 't20':
			query = query.replace('100','25')
		cursor.execute(query)
		answer = cursor.fetchall()
		if len(answer) == 0:
			result[e] = []
		else:
			result[e] = answer[0]
	query = "Select name,runs,innings,average,fifties,hundreds FROM (select id,runs,innings, average, Fifties, hundreds from odi_comp_bat WHERE runs in (select runs from odi_comp_bat where runs is not null and LOWER(country) = LOWER('India') order by runs desc limit 10) and LOWER(country) = LOWER('India')) AS players JOIN player_names ON players.id = player_names.id ORDER BY runs DESC;"
	query = query.replace('odi',game)
	query = query.replace('India',country)
	cursor.execute(query)
	bat = cursor.fetchall()
	query = "Select name,wickets,innings,bowling_avg FROM (select id,wickets,innings,bowling_avg from odi_comp_ball WHERE wickets in (select wickets from odi_comp_ball where wickets is not null and LOWER(country) = LOWER('India') order by wickets desc limit 10) and LOWER(country) = LOWER('India')) AS players JOIN player_names ON players.id = player_names.id ORDER BY wickets DESC LIMIT 10"
	query = query.replace('odi',game)
	query = query.replace('India',country)
	cursor.execute(query)
	ball = cursor.fetchall()
	return result,bat,ball

def closeConnection():
	cursor.close()
	conn.close()

if __name__ == '__main__': #Will be executed if this code is run on its own
	print(executeSpecificQuery(3791))