from datetime import datetime

BAD_WORDS_FILE = "./resources/bad_words.txt"
BAD_WORDS_SET = set(open(BAD_WORDS_FILE).read().splitlines())


def next_valid_datetime(arr, i=0, key=None, reverse=False):
    """
    Takes in an array and an index and attempts to find the next valid datetime
    starting at that index. Returns the index at which that datetime exists or
    None if there are no valid datetimes afterwards.

    Paramters:
        arr :class:`list`: The list of objects with which to search for the next
            valid datetime.
        i :class:`int`: The index to start at. Defaults to 0.
        key :class:`str`: A key to access the datetime within each object if
            needed. If None, then the list is assumed to be datetimes.
        reverse :class:`bool`: If True, searches in reverse starting at -i, down
            to 0.

    Raises:
        AttributeError if key is defined and elements of the list are not
            objects.
        IndexError if i is greater than the length of arr.
    """
    arr_len = len(arr)
    if i > arr_len:
        raise IndexError
    if reverse:
        indices = reversed(range(0, arr_len - i))
    else:
        indices = range(i, arr_len)
    for index in indices:
        if key is None:
            datetime_obj = arr[index]
        else:
            datetime_obj = arr[index].get(key)
        if isinstance(datetime_obj, datetime):
            return index
    return None


def ave_or_none(total, count):
    return total / float(count) if count else None
