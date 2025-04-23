from django.shortcuts import render,redirect, get_object_or_404
from django.http import HttpResponse
from . models import Customer
from .models import Restaurants
from .models import Menu
from delivery.forms import ResForm
from delivery.forms import MenuForm
from .models import Cart
from django.contrib import messages
from django.conf import settings
import razorpay


from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import json

def index(request):
    return render(request,'delivery/index.html')

def sign_in(request):
     return render(request,'delivery/sign_in.html')
 
def sign_up(request):
     return render(request,'delivery/sign_up.html')
 
from django.shortcuts import render
from django.http import HttpResponse
from .models import Customer, Restaurants

def handle_signin(request):
    li = Restaurants.objects.all()

    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')

        try:
            # Admin login check
            if username == 'admin' and password == 'admin':
                request.session['username'] = username
                request.session['role'] = 'admin'
                return redirect('delivery:display_res')
            # Customer login check
            cus = Customer.objects.get(username=username, password=password)
            request.session['username'] = cus.username
            request.session['role'] = 'customer'
            return render(request, 'delivery/cusdisplay_res.html', {'username': cus.username, 'li': li})

        except Customer.DoesNotExist:
            return render(request, 'delivery/failed.html')

    return HttpResponse('Invalid request')

 
def handle_signup(request):
    if request.method == "POST": 
        username = request.POST.get('username')
        password = request.POST.get('password')
        email = request.POST.get('email')
        mobile = request.POST.get('mobile')
        address = request.POST.get('address')
        try:
            cus = Customer.objects.get(username = username, password = password)
        except:
            cus = Customer(username = username, password = password, email = email, mobile = mobile, address = address)
            cus.save()
        return render(request, 'delivery/sign_in.html')
    else:
        return HttpResponse('Invalid request')
    
def sign_out(request):
    request.session.flush()  # This clears the session entirely
    return redirect('delivery:sign_in')  # Or wherever your login page is

def add_res(request):
    form = ResForm(request.POST or None)
    if form.is_valid():
        res_name = request.POST.get('Res_name')
        try:
            res = Restaurants.objects.get(Res_name = res_name)
        except:
            form.save()
            return redirect('delivery:display_res')
    return render(request, 'delivery/add_res.html',{'form':form})
    
def display_res(request):
    li = Restaurants.objects.all()
    return render(request, 'delivery/display_res.html',{'li': li}) 

def view_menu(request,id):
    res = Restaurants.objects.get(pk=id)
    menu = Menu.objects.filter(res=res)
    return render(request,'delivery/menu.html',{'res':res, 'menu':menu})

def add_menu(request, id):
    restaurant = get_object_or_404(Restaurants, id=id)  # Get the restaurant by ID
    if request.method == "POST":
        form = MenuForm(request.POST, request.FILES)  # Ensure image files are processed
        if form.is_valid():
            menu = form.save(commit=False)  # Do not save to the database yet
            menu.res = restaurant  # Assign the restaurant
            menu.save()  # Save to the database
            return redirect('delivery:view_menu', id)
    else:
        form = MenuForm()

    return render(request, 'delivery/menu_form.html', {'form': form})


def delete_menu(request,id):
    item=Menu.objects.get(pk=id)
    res_id = item.res.id
    item.delete()
    return redirect('delivery:view_menu',res_id)

def cusdisplay_res(request,username):
    customer = Customer.objects.get(username = username)
    li = Restaurants.objects.all()
    return render(request, 'delivery/cusdisplay_res.html',{'li': li, 'username':username}) 

def cusmenu(request,id,username):
    res = Restaurants.objects.get(pk=id)
    menu = Menu.objects.filter(res=res)
    return render(request,'delivery/cusmenu.html',{'res':res, 'menu':menu,'username':username})

def update_res(request, id):
    res = Restaurants.objects.get(id=id)  # Fetch the restaurant to update
    form = ResForm(request.POST or None, instance=res)  # Bind instance
    if request.method == 'POST':
        if form.is_valid():
            form.save()
            return redirect('delivery:display_res')  # Redirect after update
    return render(request, 'delivery/update_res.html', {'form': form})

def delete_res(request,id):
    item=Restaurants.objects.get(pk=id)
    item.delete()
    return redirect('delivery:display_res')

def show_cart(request,username):
    customer = Customer.objects.get(username=username)
    cart = Cart.objects.filter(customer=customer).first()
    items = cart.items.all() if cart else []
    total_price = cart.total_price() if cart else 0
    return render(request,'delivery/show_cart.html',{'items':items,'total_price':total_price,'username':username})

def add_to_cart(request,username,menuid):
    customer = Customer.objects.get(username = username)
    item = Menu.objects.get(pk=menuid)
    cart, created = Cart.objects.get_or_create(customer = customer)
    cart.items.add(item)
    messages.success(request,f"{item.item_name} added")
    return redirect('delivery:cusmenu', id = item.res.id,username=username)

def checkout(request, username):
    customer = Customer.objects.get(username = username)
    cart = Cart.objects.filter(customer = customer).first()
    cart_items = cart.items.all() if cart else []
    total_price = cart.total_price() if cart else 0

    if total_price == 0:
        return render(request, 'delivery/checkout.html',{'error':'Your cart is Empty'})

    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

    order_data = {
        'amount':int(total_price * 100),
        'currency':'INR',
        'payment_capture':'1',
    }
    order = client.order.create(data = order_data)
    return render(
        request, 'delivery/checkout.html',
        {'username':username,
        'cart_items':cart_items,
        'total_price':total_price,
        'razorpay_key_id':settings.RAZORPAY_KEY_ID,
        'order_id':order['id'],
        'amount':total_price,
        }
    )
    
def orders(request, username):
        customer = Customer.objects.get(username = username)
        cart = Cart.objects.filter(customer=customer).first()
        cart_items = cart.items.all() if cart else []
        total_price = cart.total_price() if cart else 0

        if cart:
            cart.items.clear()

        return render(request, 'delivery/orders.html',{
        'username':username,
        'cart_items':cart_items,
        'total_price':total_price,
        'customer':customer
        })
        



from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json

from django.http import JsonResponse
import json

# Chat response logic with memory
def chat_view(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        user_message = data.get('message', '').lower()

        # Initialize chat memory
        if 'chat_context' not in request.session:
            request.session['chat_context'] = ''

        # Dictionary of keyword groups and their responses
        grouped_keywords_responses = {
            ("hi", "hello", "hey", "hii"): "Hello! How can I assist you with MealMate?",
            ("mealmate", "meal mate", "about mealmate"): "MealMate helps you discover restaurants and order your favorite meals online!",
            ("menu", "view menu", "food list", "show menu", "menu list"): "You can view menus by visiting any restaurant's page or clicking 'View Menu'.",
            ("restaurant", "restaurants", "food places"): "We have many great restaurants. Choose your favorite and explore their menu.",
            ("order", "how to order", "place order", "ordering food", "order food"): "To place an order, go to a restaurant's menu and add items to your cart.",
            ("cart", "show cart", "my cart", "check cart", "what's in my cart"): "Click the 'Show Cart' button to view or edit your selected items.",
            ("signup", "sign up", "create account", "register"): "You can sign up using the 'Sign-Up' button on the top right corner.",
            ("signin", "sign in", "login", "log in"): "Already have an account? Use the 'Sign-In' button to access your dashboard.",
            ("home", "homepage", "front page", "go home"): "Click the MealMate logo or 'Home' in the navbar to go to the homepage.",
            ("help", "need help", "support", "assistance"): "I'm here to assist! Ask about signing in, menus, orders, or anything else.",
            ("contact", "reach out", "talk to support"): "You can reach out via the contact section on our homepage.",
            ("who are you", "what is this", "who made you"): "I'm your MealMate assistant chatbot! Here to help with all your food needs.",
            ("thank you", "thanks", "ty", "thankyou"): "You're welcome! 😊 Let me know if you need anything else.",
            ("bye", "goodbye", "see you", "exit"): "Goodbye! Have a tasty day with MealMate 🍽️!"
        }

        # Try to find a matching keyword
        matched = False
        for keywords, reply in grouped_keywords_responses.items():
            if any(keyword in user_message for keyword in keywords):
                matched = True
                request.session['chat_context'] = keywords[0]  # Store the context
                return JsonResponse({'reply': reply})

        # If no match, use context to give smart reply
        context = request.session.get('chat_context', '')
        if context:
            if context in ("menu", "restaurant"):
                return JsonResponse({'reply': "Are you looking for specific food items or restaurant types?"})
            elif context in ("order", "cart"):
                return JsonResponse({'reply': "Would you like help placing the order or reviewing your cart?"})
            elif context in ("signin", "signup"):
                return JsonResponse({'reply': "Do you need help accessing your account or creating one?"})
            else:
                return JsonResponse({'reply': "Can you tell me a bit more so I can help better?"})

        # Default fallback
        return JsonResponse({'reply': "I'm not sure I understood that. You can ask about menu, restaurants, orders, or signing in!"})

    return JsonResponse({'reply': "Invalid request method."})
