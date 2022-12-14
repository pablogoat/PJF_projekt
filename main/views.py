from ctypes import sizeof
from unicodedata import name
from django.shortcuts import redirect, render
from django.http import HttpResponseRedirect

from django.contrib.auth.models import User
from main.models import Person, Sheet, Item, Debtor, SharedSheet
from .forms import addItem, addPerson, sheetCreator, linkPerson
from main.transaction import transaction

# Create your views here.

# base home page
def home(response): 

    color = "#00ff00"
    return render(response, "main/home.html", {"col": color})

# page for creating new sheet
def create(response): 
    if response.method == 'POST':
        print(response.POST)
        form = sheetCreator(response.POST)

        if form.is_valid():
            t = Sheet(name=form.cleaned_data["name"])
            t.save()
            response.user.sheet.add(t)

        return HttpResponseRedirect('/', {})
    else:
        form = sheetCreator()

        return render(response, "main/create.html", {"form": form})

# page displaying all sheets
def allsheets(response): 

    if response.method == 'POST':
        print(response.POST)

        return HttpResponseRedirect('/reckon/%d' %int(response.POST.get("edit")))

    elif response.user.is_authenticated:
        sheets = response.user.sheet.all()
        shared = response.user.sharedsheet.all()
        shared = list(map(lambda a: a.sheet, shared))

        return render(response, "main/sheets.html", {"sheets": sheets, "shared": shared})
    else:
        return render(response, "main/sheets.html", {"sheets": ()})

# page displaying one chosen sheet
def reckon(response, sheetid):

    if response.method == 'POST':
        # delete sheet
        if response.POST.get("delete"):
            view = Sheet.objects.get(user=response.user, name=response.POST.get("delete"))
            view.delete()

            return HttpResponseRedirect('/sheets/', {})
        # add new person
        elif response.POST.get("addperson"):
            view = Sheet.objects.get(user=response.user, name=response.POST.get("addperson"))
            addperson = addPerson(response.POST)
            
            if addperson.is_valid():
                person = Person(sheet=view, name=addperson.cleaned_data["name"])
                print(person)
                person.save()

            return HttpResponseRedirect('/sheets/', {})
        # add new item
        elif response.POST.get("additem"):
            view = Sheet.objects.get(user=response.user, name=response.POST.get("additem"))
            additem = addItem(response.POST)

            postPay = response.POST.get("pay")
            print(postPay)

            if additem.is_valid():

                postValue = additem.cleaned_data["value"]
                postItem = additem.cleaned_data["item"]
                print("||||||||||||") #www
                print(postValue)
                print(postItem)

                if Person.objects.filter(sheet=view, name=postPay).exists():
                    new_item = Item(sheet=view, person=Person.objects.get(sheet=view, name=postPay), name=postItem, value=postValue)
                    print(new_item)
                    test = Person.objects.get(sheet=view, name=postPay)
                    test.balance -= postValue
                    test.save()
                    new_item.save()
                else:
                    newPerson = Person(sheet=view, name=postPay, balance=-postValue)
                    print(newPerson)
                    newPerson.save()

                    new_item = Item(sheet=view, person=newPerson, name=postItem, value=postValue)
                    print(new_item)
                    new_item.save()

                view.unapproved_item = postItem
                view.save()

                return HttpResponseRedirect('/reckon/{}/{}'.format(view.id, postItem))

            return HttpResponseRedirect('/reckon/{}'.format(view.id))
        # summarize reckoning
        elif response.POST.get("show"):
            #view = Sheet.objects.get(user=response.user, id=int(response.POST.get("show")))
            if not Sheet.objects.filter(user=response.user, id=int(response.POST.get("show"))).exists():
                s = Sheet.objects.get(id=int(response.POST.get("show")))
                view = SharedSheet.objects.get(user=response.user, sheet=s)
                if view:
                    view = view.sheet
            else:
                view = Sheet.objects.get(user=response.user, id=sheetid)
            
            return HttpResponseRedirect('/{}/transactions'.format(view.id))
        # delete item
        elif response.POST.get("item_delete"):
            view = Sheet.objects.get(user=response.user, id=sheetid)
            item = Item.objects.get(sheet=view, name=response.POST.get("item_delete"))

            item.person.balance += item.value
            item.person.save()

            for debtor in Debtor.objects.filter(item=item):
                debtor.person.balance -= debtor.share/100 * item.value
                debtor.person.save()

            item.delete()

            return HttpResponseRedirect('/sheets/', {})
        elif response.POST.get("linkperson"):
            view = Sheet.objects.get(user=response.user, id=response.POST.get("linkperson"))
            linkperson = linkPerson(response.POST)

            if linkperson.is_valid() and User.objects.get(id=linkperson.cleaned_data["name"]):
                link = SharedSheet(user=User.objects.get(id=linkperson.cleaned_data["name"]),sheet=view)
                print(link)
                link.save()
            return HttpResponseRedirect('/sheets/', {})
        else:
            return HttpResponseRedirect('/', {})

    # default
    else:
        #view = Sheet.objects.get(user=response.user, id=sheetid)
        if not Sheet.objects.filter(user=response.user, id=sheetid).exists():
            s = Sheet.objects.get(id=sheetid)
            view = SharedSheet.objects.get(user=response.user, sheet=s)
            if view:
                view = view.sheet
        else:
            view = Sheet.objects.get(user=response.user, id=sheetid)
        
        ownership = True
        if view.user != response.user:
            ownership = False

        print(view)

        # if user quits splitting an expense the item gets deleted
        if view.unapproved_item != '':
            item_to_delete = Item.objects.get(sheet=view, name=view.unapproved_item)

            item_to_delete.person.balance += item_to_delete.value
            item_to_delete.person.save()

            for debtor in Debtor.objects.filter(item=item_to_delete):
                debtor.person.balance -= debtor.share/100 * item_to_delete.value
                debtor.person.save()

            item_to_delete.delete()
            view.unapproved_item = ''
            view.save()

        people = [i for i in Person.objects.filter(sheet=view)]
        for item in Item.objects.filter(sheet=view):
            item.value = round(item.value,2)
        items = [i for i in Item.objects.filter(sheet=view)]
        debtors = [[i.person.name for i in Debtor.objects.filter(item=j)] for j in Item.objects.filter(sheet=view)]
        print(debtors)

        addperson = addPerson()
        additem = addItem()
        linkperson = linkPerson()

        return render(response, "main/reckon.html",
            {"view": view, "people": people, "items": items, "debtors": debtors,
            "addperson": addperson, "additem": additem, "linkperson": linkperson, "ownership": ownership})

#function for spliting an expense among people
def debet(response, sheetid, new_item): 

    view = Sheet.objects.get(user=response.user, id=sheetid)

    if response.method == 'POST':

        sum_share = 100
        count = 0

        for person in Person.objects.filter(sheet=view):
            if response.POST.get(person.name) == 'clicked':
                count += 1
                if response.POST.get('d' + person.name) != '':
                    sum_share -= float(response.POST.get('d' + person.name))
                    count -= 1
            print(count)
                

        for p in Person.objects.filter(sheet=view):
            if response.POST.get(p.name) == 'clicked':
                if response.POST.get('d' + p.name) != '':
                    new_Debtor = Debtor(person=p, item=Item.objects.get(sheet=view, name=new_item), share=float(response.POST.get('d' + p.name)))
                else:
                    print(count)
                    new_Debtor = Debtor(person=p, item=Item.objects.get(sheet=view, name=new_item), share=sum_share/count)
                    sum_share -= new_Debtor.share
                    count -= 1
                new_Debtor.person.balance += float(new_Debtor.item.value * new_Debtor.share/100)
                new_Debtor.person.save()
                new_Debtor.save()
                print(str(new_Debtor.item) + " " + new_Debtor.person.name + " " + str(new_Debtor.share))

        view.unapproved_item = ''
        view.save()

        return HttpResponseRedirect('/sheets/', {})

    
    else:
        debt = [i for i in Person.objects.filter(sheet=view)]

        return render(response, "main/debet.html",
        {"debt": debt, "view": view, "item": Item.objects.get(sheet=view, name=new_item)})

#function that shows transactions needed to complete the reckoning
def transactions(response, sheetid): 
    #view = Sheet.objects.get(user=response.user, id=sheetid)
    if not Sheet.objects.filter(user=response.user, id=sheetid).exists():
        s = Sheet.objects.get(id=sheetid)
        view = SharedSheet.objects.get(user=response.user, sheet=s)
        if view:
            view = view.sheet
    else:
        view = Sheet.objects.get(user=response.user, id=sheetid)
    
    debtors = [person for person in Person.objects.filter(sheet=view) if person.balance > 0]
    collectors = [person for person in Person.objects.filter(sheet=view) if person.balance < 0]

    # sorting debtors that the one with the highest bill comes first
    debtors.sort(reverse=True, key=PersonCmp)
    # sorting collectors that the one with the lowest balance comes first
    collectors.sort(reverse=True, key=PersonCmp)

    print(debtors)
    print(collectors)

    actions = []

    # create transactions till run out of debtors and collectors
    while len(debtors) and len(collectors): 
        if debtors[0].balance < collectors[0].balance * -1:
            actions.append(transaction(debtors[0].name,str(round(debtors[0].balance,2)),collectors[0].name))
            collectors[0].balance += debtors[0].balance
            debtors.pop(0)
        elif debtors[0].balance == collectors[0].balance * -1:
            actions.append(transaction(debtors[0].name,str(round(debtors[0].balance,2)),collectors[0].name))
            collectors.pop(0)
            debtors.pop(0)
        else:
            actions.append(transaction(debtors[0].name,str(round(collectors[0].balance * -1,2)),collectors[0].name))
            debtors[0].balance += collectors[0].balance
            collectors.pop(0)

    for i in actions:
        if float(i.value) == 0.0:
            actions.remove(i)
            
    print(actions)

    return render(response, 'main/transactions.html', {"actions": actions, "sheet": view})

def PersonCmp(p1):
    
    return p1.balance