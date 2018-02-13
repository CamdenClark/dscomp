drop table if exists submissions;
drop table if exists users;
create table users (
	userid integer primary key autoincrement,
	name text not null,
	email text not null,
	password text not null,
	admin int not null
);
create table submissions (
	subid integer primary key autoincrement,
	userid integer not null,
        timestamp text not null,	
	privatescore real not null,
	publicscore real not null,
	foreign key(userid) references users(userid)
);
