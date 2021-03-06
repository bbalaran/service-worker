import psycopg2
import redis
import sys

lang_list = ['Python', 'JavaScript', 'R', 'Go']

try:
    conn = psycopg2.connect("dbname='halcyon' user='postgres' host='localhost' password='hi'")
except:
    print ("I am unable to connect to the database")

try:
    r = redis.StrictRedis(host='localhost', port=6379, db=0)
except:
    print ("I am unable to connect to redis")

def insertVelocities(num_repos=10):
  for lang in lang_list:
      for base_stars, exponent in [[400, 6], [100, 6], [400, 8]]:
          print('currently processing weekly for: ', lang, base_stars, exponent)
          pipe = r.pipeline()
          # current week's
          pipe.delete('%s:curr_week_%s_%s'%(lang, base_stars, exponent))
          cur = conn.cursor()
          cur.execute(
              """select repo_name, language, num_stars, stars, stars::real / ((num_stars::real+%s)^(1.%s) ) AS normalized_stars
              From
              (
                  select repo_id, repo_name, language, num_stars, count(*) AS stars from halcyon."Test_Hourly_Watches"
                  Inner Join halcyon."Test_Repos" On repo_id = id
                  where num_stars > 0
                  AND date > '2015-12-24'
                  AND date <=  '2015-12-31'
                  group by repo_id, repo_name, language, num_stars order by num_stars desc
              ) AS x
              where language Like '%s'
              order by normalized_stars desc
              limit %s""" %(base_stars, exponent, lang, num_repos) )
          rows_curr = cur.fetchall()
          for row in rows_curr:
              pipe.zadd('%s:curr_week_%s_%s'%(lang, base_stars, exponent), row[4], row[0])

          # prev week's
          pipe.delete('%s:prev_week_%s_%s'%(lang, base_stars, exponent))
          cur = conn.cursor()
          cur.execute(
              """select repo_name, language, num_stars, stars, stars::real / ((num_stars::real+%s)^(1.%s) ) AS normalized_stars
              From
              (
                  select repo_id, repo_name, language, num_stars, count(*) AS stars from halcyon."Test_Hourly_Watches"
                  Inner Join halcyon."Test_Repos" On repo_id = id
                  where num_stars > 0
                  AND date > '2015-12-17'
                  AND date <=  '2015-12-24'
                  group by repo_id, repo_name, language, num_stars order by num_stars desc
              ) AS x
              where language Like '%s'
              order by normalized_stars desc
              limit %s""" %(base_stars, exponent, lang, num_repos) )
          rows_prev = cur.fetchall()
          for row in rows_prev:
              pipe.zadd('%s:prev_week_%s_%s'%(lang, base_stars, exponent), row[4], row[0])

          # insert and delete all as single transaction
          pipe.execute()



if __name__ == "__main__":
    try:
        num_of_repos_want_for_each_leaderboard = sys.argv[1]
    except IndexError:
        print("Usage: myprogram.py <date>\n date: YYYY-MM-DD-HH, for ex: 2016-02-01-15")
        sys.exit(1)

    # start inserting rows into redis
    insertVelocities(num_of_repos_want_for_each_leaderboard)
