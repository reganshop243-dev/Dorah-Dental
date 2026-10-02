import 'package:flutter/material.dart';
import '../services/api_service.dart';
import 'home_screen.dart';

class LoginScreen extends StatefulWidget { const LoginScreen({super.key}); @override State<LoginScreen> createState() => _LoginScreenState(); }
class _LoginScreenState extends State<LoginScreen> {
  final id = TextEditingController(); final pin = TextEditingController(); bool loading = false; String? error;
  @override void dispose(){id.dispose();pin.dispose();super.dispose();}
  Future<void> login() async {
    setState(() {loading=true;error=null;});
    try { await ApiService.login(id.text.trim(), pin.text.trim()); if(mounted) Navigator.of(context).pushReplacement(MaterialPageRoute(builder:(_)=>const HomeScreen())); }
    catch(e){setState(()=>error=e.toString().replaceFirst('Exception: ',''));}
    finally{if(mounted)setState(()=>loading=false);}
  }
  @override Widget build(BuildContext context)=>Scaffold(body: SafeArea(child: Center(child: SingleChildScrollView(padding: const EdgeInsets.all(26), child: ConstrainedBox(constraints: const BoxConstraints(maxWidth: 430), child: Column(children:[
    Image.asset('assets/dental_logo.png',height:110), const SizedBox(height:18),
    const Text('Dorah Dental',style: TextStyle(fontSize:30,fontWeight:FontWeight.w800,color:Color(0xFF1A5276))),
    const SizedBox(height:6), const Text('Your private patient care portal',style:TextStyle(color:Colors.black54)), const SizedBox(height:32),
    TextField(controller:id,keyboardType:TextInputType.phone,decoration:const InputDecoration(labelText:'Phone number or Patient ID',prefixIcon:Icon(Icons.person_outline))), const SizedBox(height:14),
    TextField(controller:pin,keyboardType:TextInputType.number,obscureText:true,maxLength:6,decoration:const InputDecoration(labelText:'6-digit PIN',prefixIcon:Icon(Icons.lock_outline),counterText:'')),
    if(error!=null) Padding(padding:const EdgeInsets.only(top:14),child:Text(error!,style:const TextStyle(color:Colors.red))), const SizedBox(height:24),
    SizedBox(width:double.infinity,height:54,child:ElevatedButton(onPressed:loading?null:login,style:ElevatedButton.styleFrom(backgroundColor:const Color(0xFF1A5276),foregroundColor:Colors.white,shape:RoundedRectangleBorder(borderRadius:BorderRadius.circular(14))),child:loading?const CircularProgressIndicator(color:Colors.white):const Text('Sign in',style:TextStyle(fontSize:16,fontWeight:FontWeight.bold)))),
    const SizedBox(height:20), const Text('Your PIN is private. Never share it with anyone.',textAlign:TextAlign.center,style:TextStyle(color:Colors.black45)),
  ]))))));
}
