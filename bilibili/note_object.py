from typing import Tuple, List

class NoteObject:
    def __init__(self, obj: List[dict] = None, length: int = 0) -> None:
        self.obj = obj if obj else []
        self.length = length

    def __add__(self, other: 'NoteObject') -> 'NoteObject':
        new_obj = self.obj.copy()
        new_obj.extend(other.obj)
        return NoteObject(new_obj, self.length + other.length)

    def append(self, obj: dict, len: int) -> None:
        self.obj.append(obj)
        self.length += len

    def appendNewLine(self, align: str = None) -> None:
        if not align:
            self.obj.append({ "insert": "\n" })
        else:
            self.obj.append({
                "attributes": { 'align': align },
                "insert": "\n"
            })
        self.length += 1
