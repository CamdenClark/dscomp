drop table if exists submissions;
drop table if exists users;
create table users (
	userid integer primary key autoincrement,
	name text not null,
	email text not null,
	password text not null,
	admin int not null
);

create table pages (
	pageid integer primary key autoincrement,
	page text,
	content text
);

insert into pages (page, content) values ('train', 'This is a train dataset. Look, you can use **markdown**! ~~');
insert into pages (page, content) values ('test', 'This is a test dataset. Look, you can use **markdown**! ~~');
insert into pages (page, content) values ('about', 'This is an about page. Look, you can use **markdown**! ~~');
insert into pages (page, content) values ('scoring', 'This describes a scoring page. Look, you can use **markdown**! ~~');

create table submissions (
	subid integer primary key autoincrement,
	userid integer not null,
        timestamp text not null,	
	privatescore real not null,
	publicscore real not null,
	notes text,
	foreign key(userid) references users(userid)
);
