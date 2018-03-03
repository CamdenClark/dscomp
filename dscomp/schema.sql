drop table if exists submissions;
drop table if exists users;
create table users (
    userid integer primary key auto_increment,
    name text not null,
    email text not null,
    password text not null,
    admin int not null
);

create table pages (
    pageid integer primary key auto_increment,
    page text,
    content text
);

insert into pages (page, content) values ('train', 'This is a train dataset. Look, you can use **markdown**! ~~');
insert into pages (page, content) values ('test', 'This is a test dataset. Look, you can use **markdown**! ~~');
insert into pages (page, content) values ('about', 'This is an about page. Look, you can use **markdown**! ~~');
insert into pages (page, content) values ('scoring', 'This describes a scoring page. Look, you can use **markdown**! ~~');

create table submissions (
    subid integer primary key auto_increment,
    userid integer not null,
    timestamp timestamp not null,    
    privatescore real not null,
    publicscore real not null,
    notes text,
    foreign key(userid) references users(userid)
);
