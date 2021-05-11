from datetime import datetime

class BaseUser:
    """Base class that details common operations on a Roblox user.

    The following implement this class:

    - :class:`roblox.User`
    - :class:`roblox.Member`

    .. container:: operations

        .. describe str(x)

            Returns the user's name.

        .. describe int(x)

            Returns the user's unique id.
    
    Attributes
    -----------
    name: :class:`str`
        The user's username.
    id: :class:`int`
        The user's unique id.
    display_name: :class:`int`
        The user's display name.
    profile_url: :class:`str`
        The user's Roblox profile url.
    avatar_url: :class:`str`
        The user's avatar url.
    """
    __slots__ = ('name', 'id', 'display_name', 'profile_url', 'avatar_url')

    def __init__(self, *, data) -> None:
        self._update(data)

    def __repr__(self) -> str:
        return f"<BaseUser id={self.id} name={self.name}>"

    def __str__(self) -> str:
        return self.name

    def __int__(self) -> int:
        return self.id

    def _update(self, data):
        self.name = data['name']
        self.id = data['id']
        self.display_name = data['displayName']
        self.profile_url = f"https://www.roblox.com/users/{self.id}/profile"
        self.avatar_url = f"http://www.roblox.com/Thumbs/Avatar.ashx?x=720&y=720&Format=Png&username={self.name}"

class User(BaseUser):
    """Represents a Roblox user.

    .. container:: operations

        .. describe x == y

            Checks if two users are equal.

        .. describe x != y

            Checks if two users are not equal.

        .. describe str(x)

            Returns the user's name.

        .. describe int(x)

            Returns the user's unique id.

    Attributes
    -----------
    name: :class:`str`
        The user's username.
    id: :class:`int`
        The user's unique id.
    display_name: :class:`str`
        The user's display name.
    description: :class:`str`
        The user's account description.
    created: :class:`datetime.datetime`
        When the user's account was created.
    banned: :class:`bool`
        Whether the user has been banned from Roblox.
    profile_url: :class:`str`
        The user's Roblox profile url.
    avatar_url: :class:`str`
        The user's avatar url.
    """
    __slots__ = BaseUser.__slots__ + ('description', 'created', 'banned')

    def __init__(self, *, data) -> None:
        super().__init__(data=data)

    def __repr__(self) -> str:
        return f"<User id={self.id} name={self.name} created={self.created!r} banned={self.banned}>"

    def __eq__(self, o:object) -> bool:
        return isinstance(o, BaseUser) and o.id == self.id

    def __ne__(self, o: object) -> bool:
        return not self.__eq__(o)
    
    def _roblox_time(self, object) -> datetime:
        return datetime.strptime(object, '%Y-%m-%dT%H:%M:%S.%fZ')

    def _update(self, data):
        super()._update(data)
        self.description = data.get('description')
        self.created = self._roblox_time(data['created'])
        try:
            self.banned = data['banned']
        except KeyError:
            self.banned = data['isBanned']

class Role:
    """Represents a Role in a Roblox group.

    .. container:: operations

        .. describe x == y

            Checks if two roles are equal.

        .. describe x != y

            Checks if two roles are not equal.

        .. describe str(x)

            Returns the role's name.

        .. describe int(x)

            Returns the role's id.

        .. describe len(x)

            Returns the number of user's who have the role.

    Attributes
    -----------
    name: :class:`str`
        The role's name.
    id: :class:`int`
        The role's id.
    rank: :class:`int`
        The role's rank.
    membercount: :class:`int`
        The number of users who have this role.
    """
    __slots__ = ('id', 'name', 'rank', 'membercount')

    def __init__(self, *, data) -> None:
        self._update(data)

    def __repr__(self) -> str:
        return f"<Role id={self.id} name={self.name} rank={self.rank} membercount={self.membercount}>"

    def __str__(self) -> str:
        return self.name

    def __int__(self) -> int:
        return self.id

    def __eq__(self, o: object) -> bool:
        return isinstance(o, Role) and o.id == self.id

    def __ne__(self, o: object) -> bool:
        return not self.__eq__(o)
        
    def __len__(self) -> int:
        return len(self.membercount)

    def _update(self, data) -> None:
        self.id = data['id']
        self.name = data['name']
        self.rank = data['rank']
        self.membercount = data.get('memberCount', 0)

class Member(BaseUser):
    """Represents a Member in a Roblox group.

    .. container:: operations

        .. describe x == y

            Checks if two users are equal.

        .. describe x != y

            Checks if two users are not equal.

        .. describe str(x)

            Returns the user's name.

        .. describe int(x)

            Returns the user's unique id.

    
    Attributes
    -----------
    name: :class:`str`
        The user's username.
    id: :class:`int`
        The user's unique id.
    display_name: :class:`int`
        The user's display name.
    role: :class:`roblox.Role`
        The user's role.
    profile_url: :class:`str`
        The user's Roblox profile url.
    avatar_url: :class:`str`
        The user's avatar url.
    group_id: :class:`int`
        The group id of the Group the user is in.
    """
    __slots__ = BaseUser.__slots__ + ('role','group_id')

    def __init__(self, *, data, group_id) -> None:
        super().__init__(data=data)
        self.group_id = group_id

    def __repr__(self) -> str:
        return f"<Member id={self.id!r} name={self.name!r} role={self.role!r} group_id={self.group_id!r}>"

    def __eq__(self, o: object) -> bool:
        return isinstance(o, BaseUser) and o.id == self.id

    def __ne__(self, o: object) -> bool:
        return not self.__eq__(o)

    def _update(self, data):
        super()._update(data)
        self.role = Role(data=data.get('role'))
